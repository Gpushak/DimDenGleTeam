import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/main.scss'

const savedTheme = localStorage.getItem('qwentory.theme')
document.documentElement.dataset.theme = savedTheme === 'light' ? 'light' : 'dark'

createApp(App).use(createPinia()).mount('#app')
