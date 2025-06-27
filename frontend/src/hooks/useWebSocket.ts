import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  data: any;
}

export interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectDelay?: number;
  maxReconnectAttempts?: number;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface UseWebSocketReturn {
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  sendMessage: (message: WebSocketMessage) => void;
  lastMessage: WebSocketMessage | null;
  reconnect: () => void;
}

export const useWebSocket = (options: UseWebSocketOptions): UseWebSocketReturn => {
  const {
    url,
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectDelay = 3000, // 降低基础延迟
    maxReconnectAttempts = 10, // 增加最大重连次数
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutId = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalId = useRef<NodeJS.Timeout | null>(null);
  const isMounted = useRef(true);
  const lastConnectAttempt = useRef<number>(0);
  const isReconnecting = useRef(false);

  // 心跳处理
  const startHeartbeat = useCallback(() => {
    // 清除之前的心跳
    if (heartbeatIntervalId.current) {
      clearInterval(heartbeatIntervalId.current);
    }
    
    // 启动新的心跳
    heartbeatIntervalId.current = setInterval(() => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        try {
          ws.current.send(JSON.stringify({
            type: 'ping',
            timestamp: Date.now()
          }));
        } catch (error) {
          console.warn('发送心跳失败:', error);
        }
      }
    }, 25000); // 每25秒发送一次心跳
  }, []);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalId.current) {
      clearInterval(heartbeatIntervalId.current);
      heartbeatIntervalId.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!isMounted.current || isReconnecting.current) return;
    
    // 防止频繁连接尝试
    const now = Date.now();
    if (now - lastConnectAttempt.current < 2000) {
      return;
    }
    lastConnectAttempt.current = now;
    isReconnecting.current = true;
    
    try {
      // 如果已经有连接，先关闭
      if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
        ws.current.close();
      }

      setConnectionStatus('connecting');
      ws.current = new WebSocket(url);

      // 设置连接超时
      const connectTimeout = setTimeout(() => {
        if (ws.current && ws.current.readyState === WebSocket.CONNECTING) {
          ws.current.close();
          console.warn('WebSocket连接超时');
        }
      }, 15000); // 15秒超时

      ws.current.onopen = () => {
        if (!isMounted.current) return;
        clearTimeout(connectTimeout);
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        isReconnecting.current = false;
        console.log('WebSocket连接成功');
        
        // 启动心跳
        startHeartbeat();
        
        onOpen?.();
      };

      ws.current.onmessage = (event) => {
        if (!isMounted.current) return;
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          // 处理心跳消息
          if (message.type === 'heartbeat') {
            // 响应心跳
            if (ws.current && ws.current.readyState === WebSocket.OPEN) {
              ws.current.send(JSON.stringify({
                type: 'pong',
                timestamp: Date.now()
              }));
            }
            return;
          }
          
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('解析WebSocket消息失败:', error);
        }
      };

      ws.current.onclose = (event) => {
        if (!isMounted.current) return;
        clearTimeout(connectTimeout);
        stopHeartbeat();
        setIsConnected(false);
        setConnectionStatus('disconnected');
        isReconnecting.current = false;
        onClose?.();

        // 智能重连策略
        if (reconnectAttempts.current < maxReconnectAttempts && !event.wasClean && isMounted.current) {
          reconnectAttempts.current++;
          
          // 指数退避算法，但限制最大延迟
          const baseDelay = reconnectDelay;
          const backoffMultiplier = Math.min(Math.pow(1.5, reconnectAttempts.current - 1), 8);
          const jitter = Math.random() * 1000; // 添加随机抖动
          const finalDelay = Math.min(baseDelay * backoffMultiplier + jitter, 30000);
          
          console.log(`WebSocket重连 (${reconnectAttempts.current}/${maxReconnectAttempts}) 延迟: ${Math.round(finalDelay)}ms`);
          
          // 清除之前的重连定时器
          if (reconnectTimeoutId.current) {
            clearTimeout(reconnectTimeoutId.current);
          }
          
          reconnectTimeoutId.current = setTimeout(() => {
            if (isMounted.current && reconnectAttempts.current <= maxReconnectAttempts) {
              connect();
            }
          }, finalDelay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          console.log('WebSocket达到最大重连次数，进入离线模式');
          setConnectionStatus('error');
        }
      };

      ws.current.onerror = (error) => {
        if (!isMounted.current) return;
        clearTimeout(connectTimeout);
        stopHeartbeat();
        isReconnecting.current = false;
        console.warn('WebSocket连接失败，将尝试重连');
        setConnectionStatus('error');
        onError?.(error);
      };
    } catch (error) {
      console.error('WebSocket连接失败:', error);
      setConnectionStatus('error');
      isReconnecting.current = false;
    }
  }, [url, onMessage, onOpen, onClose, onError, reconnectDelay, maxReconnectAttempts, startHeartbeat, stopHeartbeat]);

  const disconnect = useCallback(() => {
    isMounted.current = false;
    isReconnecting.current = false;
    
    // 清理定时器
    if (reconnectTimeoutId.current) {
      clearTimeout(reconnectTimeoutId.current);
      reconnectTimeoutId.current = null;
    }
    
    stopHeartbeat();
    
    if (ws.current) {
      // 确保WebSocket连接完全关闭
      if (ws.current.readyState !== WebSocket.CLOSED) {
        ws.current.close();
      }
      ws.current = null;
    }
    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, [stopHeartbeat]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket未连接，无法发送消息');
    }
  }, []);

  const reconnect = useCallback(() => {
    console.log('手动重连WebSocket...');
    
    // 清理状态
    if (reconnectTimeoutId.current) {
      clearTimeout(reconnectTimeoutId.current);
      reconnectTimeoutId.current = null;
    }
    
    reconnectAttempts.current = 0;
    isMounted.current = true;
    isReconnecting.current = false;
    
    // 先断开现有连接
    if (ws.current) {
      ws.current.close();
    }
    
    // 稍后重连
    setTimeout(() => {
    connect();
    }, 1000);
  }, [connect]);

  useEffect(() => {
    isMounted.current = true;
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    connectionStatus,
    sendMessage,
    lastMessage,
    reconnect,
  };
}; 