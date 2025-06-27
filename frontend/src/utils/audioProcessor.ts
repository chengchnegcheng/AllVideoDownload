/**
 * 音频处理实用工具
 * 
 * 在前端处理音频文件，将其转换为适合Whisper模型的格式
 */

export interface AudioProcessingOptions {
  targetSampleRate?: number;
  targetChannels?: number;
  maxDuration?: number;
  normalizeVolume?: boolean;
}

export interface AudioInfo {
  duration: number;
  sampleRate: number;
  channels: number;
  samples: number;
  fileSize: number;
}

export class AudioProcessor {
  private audioContext: AudioContext | null = null;

  constructor() {
    this.initializeAudioContext();
  }

  /**
   * 初始化音频上下文
   */
  private initializeAudioContext() {
    try {
      // 创建音频上下文
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioContextClass();
      
      // 处理浏览器的自动播放策略
      if (this.audioContext.state === 'suspended') {
        console.log('音频上下文被暂停，需要用户交互来恢复');
      }
    } catch (error) {
      console.error('音频上下文初始化失败:', error);
      this.audioContext = null;
    }
  }

  /**
   * 恢复音频上下文（处理浏览器自动播放策略）
   */
  async resumeAudioContext(): Promise<void> {
    if (this.audioContext && this.audioContext.state === 'suspended') {
      try {
        await this.audioContext.resume();
        console.log('音频上下文已恢复');
      } catch (error) {
        console.error('恢复音频上下文失败:', error);
      }
    }
  }

  /**
   * 从文件中提取音频信息
   */
  async getAudioInfo(file: File): Promise<AudioInfo> {
    try {
      const arrayBuffer = await file.arrayBuffer();
      const audioBuffer = await this.decodeAudioData(arrayBuffer);
      
      return {
        duration: audioBuffer.duration,
        sampleRate: audioBuffer.sampleRate,
        channels: audioBuffer.numberOfChannels,
        samples: audioBuffer.length,
        fileSize: file.size
      };
    } catch (error) {
      throw new Error(`获取音频信息失败: ${(error as Error).message}`);
    }
  }

  /**
   * 处理音频文件，转换为适合Whisper的格式
   */
  async processAudioFile(
    file: File, 
    options: AudioProcessingOptions = {}
  ): Promise<Float32Array> {
    const {
      targetSampleRate = 16000,
      targetChannels = 1,
      maxDuration = 30,
      normalizeVolume = true
    } = options;

    try {
      // 确保音频上下文可用
      await this.resumeAudioContext();
      
      if (!this.audioContext) {
        throw new Error('音频上下文不可用');
      }

      // 读取文件并解码
      const arrayBuffer = await file.arrayBuffer();
      const audioBuffer = await this.decodeAudioData(arrayBuffer);

      // 转换为单声道
      const monoBuffer = this.convertToMono(audioBuffer);
      
      // 重采样到目标采样率
      const resampledBuffer = await this.resampleAudio(
        monoBuffer, 
        audioBuffer.sampleRate, 
        targetSampleRate
      );
      
      // 裁剪到最大时长
      const trimmedBuffer = this.trimAudio(resampledBuffer, targetSampleRate, maxDuration);
      
      // 音量归一化
      const finalBuffer = normalizeVolume ? 
        this.normalizeAudio(trimmedBuffer) : trimmedBuffer;

      return finalBuffer;

    } catch (error) {
      throw new Error(`音频处理失败: ${(error as Error).message}`);
    }
  }

  /**
   * 解码音频数据
   */
  private async decodeAudioData(arrayBuffer: ArrayBuffer): Promise<AudioBuffer> {
    if (!this.audioContext) {
      throw new Error('音频上下文不可用');
    }

    try {
      return await this.audioContext.decodeAudioData(arrayBuffer);
    } catch (error) {
      throw new Error(`音频解码失败: ${(error as Error).message}`);
    }
  }

  /**
   * 转换为单声道
   */
  private convertToMono(audioBuffer: AudioBuffer): Float32Array {
    const channels = audioBuffer.numberOfChannels;
    const length = audioBuffer.length;
    const monoBuffer = new Float32Array(length);

    if (channels === 1) {
      // 已经是单声道
      return audioBuffer.getChannelData(0);
    }

    // 多声道混合为单声道
    for (let i = 0; i < length; i++) {
      let sum = 0;
      for (let channel = 0; channel < channels; channel++) {
        sum += audioBuffer.getChannelData(channel)[i];
      }
      monoBuffer[i] = sum / channels;
    }

    return monoBuffer;
  }

  /**
   * 重采样音频
   */
  private async resampleAudio(
    inputBuffer: Float32Array, 
    inputSampleRate: number, 
    outputSampleRate: number
  ): Promise<Float32Array> {
    if (inputSampleRate === outputSampleRate) {
      return inputBuffer;
    }

    const ratio = inputSampleRate / outputSampleRate;
    const outputLength = Math.floor(inputBuffer.length / ratio);
    const outputBuffer = new Float32Array(outputLength);

    // 简单的线性插值重采样
    for (let i = 0; i < outputLength; i++) {
      const inputIndex = i * ratio;
      const index = Math.floor(inputIndex);
      const fraction = inputIndex - index;

      if (index + 1 < inputBuffer.length) {
        // 线性插值
        outputBuffer[i] = inputBuffer[index] * (1 - fraction) + 
                         inputBuffer[index + 1] * fraction;
      } else {
        outputBuffer[i] = inputBuffer[index];
      }
    }

    return outputBuffer;
  }

  /**
   * 裁剪音频到指定时长
   */
  private trimAudio(
    audioBuffer: Float32Array, 
    sampleRate: number, 
    maxDuration: number
  ): Float32Array {
    const maxSamples = Math.floor(sampleRate * maxDuration);
    
    if (audioBuffer.length <= maxSamples) {
      return audioBuffer;
    }

    return audioBuffer.slice(0, maxSamples);
  }

  /**
   * 音频归一化
   */
  private normalizeAudio(audioBuffer: Float32Array): Float32Array {
    const normalizedBuffer = new Float32Array(audioBuffer.length);
    
    // 找到最大绝对值
    let maxValue = 0;
    for (let i = 0; i < audioBuffer.length; i++) {
      const absValue = Math.abs(audioBuffer[i]);
      if (absValue > maxValue) {
        maxValue = absValue;
      }
    }

    // 归一化到 [-1, 1] 范围
    if (maxValue > 0) {
      const scale = 1.0 / maxValue;
      for (let i = 0; i < audioBuffer.length; i++) {
        normalizedBuffer[i] = audioBuffer[i] * scale;
      }
    } else {
      normalizedBuffer.set(audioBuffer);
    }

    return normalizedBuffer;
  }

  /**
   * 从视频文件中提取音频
   */
  async extractAudioFromVideo(videoFile: File): Promise<Float32Array> {
    try {
      // 创建视频元素
      const video = document.createElement('video');
      const objectUrl = URL.createObjectURL(videoFile);
      
      return new Promise((resolve, reject) => {
        video.addEventListener('loadedmetadata', async () => {
          try {
            await this.resumeAudioContext();
            
            if (!this.audioContext) {
              throw new Error('音频上下文不可用');
            }

            // 创建媒体元素源
            const source = this.audioContext.createMediaElementSource(video);
            
            // 创建脚本处理器
            const processor = this.audioContext.createScriptProcessor(4096, 1, 1);
            const audioData: number[] = [];
            
            processor.onaudioprocess = (event) => {
              const inputBuffer = event.inputBuffer.getChannelData(0);
              audioData.push(...Array.from(inputBuffer));
            };

            // 连接音频节点
            source.connect(processor);
            processor.connect(this.audioContext.destination);

            // 播放视频以提取音频
            video.addEventListener('ended', () => {
              URL.revokeObjectURL(objectUrl);
              resolve(new Float32Array(audioData));
            });

            video.play();

          } catch (error) {
            URL.revokeObjectURL(objectUrl);
            reject(error);
          }
        });

        video.addEventListener('error', (error) => {
          URL.revokeObjectURL(objectUrl);
          reject(new Error('视频加载失败'));
        });

        video.src = objectUrl;
      });

    } catch (error) {
      throw new Error(`视频音频提取失败: ${(error as Error).message}`);
    }
  }

  /**
   * 检查文件是否为支持的音频格式
   */
  static isSupportedAudioFormat(file: File): boolean {
    const supportedFormats = [
      'audio/wav',
      'audio/mp3',
      'audio/mpeg',
      'audio/m4a',
      'audio/aac',
      'audio/ogg',
      'audio/webm'
    ];

    return supportedFormats.includes(file.type);
  }

  /**
   * 检查文件是否为支持的视频格式
   */
  static isSupportedVideoFormat(file: File): boolean {
    const supportedFormats = [
      'video/mp4',
      'video/webm',
      'video/ogg',
      'video/avi',
      'video/mov',
      'video/quicktime'
    ];

    return supportedFormats.includes(file.type);
  }

  /**
   * 估算处理时间
   */
  static estimateProcessingTime(file: File, duration?: number): number {
    const fileSize = file.size;
    const estimatedDuration = duration || (fileSize / (1024 * 1024)) * 10; // 粗略估计
    
    // 基于文件大小和时长的处理时间估算（秒）
    const baseTime = Math.max(estimatedDuration * 0.1, 2); // 至少2秒
    const sizeModifier = fileSize / (10 * 1024 * 1024); // 10MB基准
    
    return Math.ceil(baseTime * (1 + sizeModifier));
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}

// 创建全局实例
export const audioProcessor = new AudioProcessor(); 