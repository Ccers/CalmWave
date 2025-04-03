<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-100 to-white text-gray-800">
    <!-- 页面内容 -->
    <div class="flex flex-col items-center justify-center h-screen text-center px-6">
      <h2 class="text-4xl font-bold mb-4 animate-fade-in">欢迎来到 CalmWave</h2>
      <p class="text-lg text-gray-600 animate-slide-up">
        通过 AI 聊天缓解情绪，
      </p>
      <p>
        找到内心的宁静 ✨
      </p>
      <button @click="goToChat" class="mt-8 px-8 py-3 bg-blue-500 text-white rounded-full text-xl font-semibold hover:bg-blue-400 transition duration-300 shadow-lg transform hover:scale-105">
        💬 进入 AI 聊天
      </button>
    </div>
  </div>
</template>

<script>
export default {
  setup() {
    const goToChat = () => {
      uni.navigateTo({
        url: '/pages/gotochat/gotochat'
      });
    };
    return {goToChat};
  },
};
</script>

<style>
/* 进入动画 */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fade-in 1s ease-out forwards;
}

.animate-slide-up {
  animation: slide-up 1.2s ease-out forwards;
}

</style>
