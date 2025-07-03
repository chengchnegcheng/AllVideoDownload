import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

// 清理加载指示器
const loadingElement = document.querySelector('.loading')
if (loadingElement) {
  loadingElement.textContent = '正在初始化...'
}

try {
  const rootElement = document.getElementById('root')
  
  if (!rootElement) {
    throw new Error('找不到root元素')
  }

  const root = ReactDOM.createRoot(rootElement)
  root.render(<App />)

  // 清理加载指示器
  setTimeout(() => {
    if (loadingElement && loadingElement.parentNode) {
      loadingElement.remove()
    }
    clearTimeout((window as any).loadingTimeoutId || 0)
  }, 500)

} catch (error) {
  console.error('React应用初始化失败:', error)
  
  if (loadingElement && loadingElement instanceof HTMLElement) {
    loadingElement.innerHTML = `
      <div style="color: #ff4d4f; text-align: center;">
        <h3>应用加载失败</h3>
        <p>错误: ${error instanceof Error ? error.message : String(error)}</p>
        <p style="font-size: 12px; opacity: 0.7;">请检查浏览器控制台获取详细信息</p>
      </div>
    `
  }
} 