<template>
  <view class="chat-container">
    <!-- 消息列表 -->
    <scroll-view class="chat-messages" scroll-y="true">
      <view v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
        <text class="message-text">{{ msg.text }}</text>
      </view>
    </scroll-view>

    <!-- 输入框 -->
    <view class="chat-input">
      <input
        class="input-box"
        v-model="userInput"
        placeholder="输入消息..."
        @confirm="sendMessage"
      />
      <button class="send-button" @click="sendMessage">发送</button>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'

const messages = ref([{ role: 'bot', text: '你好！有什么可以帮你的吗？' }])
const userInput = ref('')

const sendMessage = () => {
  if (!userInput.value.trim()) return

  // 用户消息
  messages.value.push({ role: 'user', text: userInput.value })

  // 清空输入框
  const userMessage = userInput.value
  userInput.value = ''

  // 模拟 AI 回复（后续可接入 DeepSeek）
  setTimeout(() => {
    messages.value.push({ role: 'bot', text: `你说的是：“${userMessage}”` })
  }, 1000)
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f5f5f5;
}

.chat-messages {
  flex: 1;
  padding: 10px;
  overflow-y: auto;
}

.message {
  max-width: 70%;
  padding: 10px;
  border-radius: 10px;
  margin: 5px 0;
}

.message.user {
  align-self: flex-end;
  background-color: #0084ff;
  color: white;
}

.message.bot {
  align-self: flex-start;
  background-color: #e5e5ea;
  color: black;
}

.chat-input {
  display: flex;
  padding: 10px;
  background-color: white;
}

.input-box {
  flex: 1;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 5px;
}

.send-button {
  margin-left: 10px;
  padding: 8px 15px;
  background-color: #0084ff;
  color: white;
  border: none;
  border-radius: 5px;
}
</style>
