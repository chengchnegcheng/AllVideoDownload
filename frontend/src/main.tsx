console.log('=== 开始加载模块 ===')

// 分步加载，检查每个模块
console.log('加载React...')
import React from 'react'
console.log('React加载成功:', React.version)

console.log('加载ReactDOM...')
import ReactDOM from 'react-dom/client'
console.log('ReactDOM加载成功')

console.log('加载App组件...')
import App from './App'
console.log('App组件加载成功')

console.log('=== 主文件开始执行 ===')

// 立即更新页面显示状态
const loadingElement = document.querySelector('.loading')
if (loadingElement) {
  loadingElement.textContent = '正在初始化React...'
}

// 验证关键模块加载
console.log('React version:', React.version)
console.log('ReactDOM:', !!ReactDOM)

try {
  // 获取根元素
  const rootElement = document.getElementById('root')
  console.log('Root element:', rootElement)
  
  if (!rootElement) {
    throw new Error('找不到root元素')
  }

  // 更新状态
  if (loadingElement) {
    loadingElement.textContent = '正在创建React根...'
  }

  // 创建React根
  console.log('创建React根...')
  const root = ReactDOM.createRoot(rootElement)
  console.log('React根创建成功:', root)

  // 更新状态
  if (loadingElement) {
    loadingElement.textContent = '正在渲染App组件...'
  }

  // 渲染应用
  console.log('开始渲染App组件...')
  root.render(<App />)
  console.log('App组件渲染完成')

  // 渲染成功后的清理 - 确保加载指示器被移除
  setTimeout(() => {
    if (loadingElement) {
      // 彻底移除加载指示器
      loadingElement.remove();
      
      // 或者显示成功消息然后移除
      loadingElement.innerHTML = '<div style="color: #52c41a;">React应用加载成功！</div>';
      
      // 2秒后完全移除
      setTimeout(() => {
        if (loadingElement.parentNode) {
          loadingElement.remove();
        }
      }, 2000);
    }
    
    // 清除所有可能的超时提示
    clearTimeout((window as any).loadingTimeoutId || 0);
    
    console.log('React应用初始化完成，加载指示器已清理');
  }, 500) // 增加延迟，确保React组件完全渲染

} catch (error) {
  console.error('=== React应用初始化失败 ===')
  console.error('错误详情:', error)
  console.error('错误堆栈:', error instanceof Error ? error.stack : 'No stack available')
  
  // 显示错误信息
  if (loadingElement && loadingElement instanceof HTMLElement) {
    loadingElement.innerHTML = `
      <div style="color: #ff4d4f; text-align: center;">
        <h3>React应用加载失败</h3>
        <p>错误: ${error instanceof Error ? error.message : String(error)}</p>
        <p style="font-size: 12px; opacity: 0.7;">请检查浏览器控制台获取详细信息</p>
      </div>
    `
  }
} 