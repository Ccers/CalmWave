<template>
  <view class="mine-container" :style="{ marginTop: marginTop + 'px' }">
    <!-- 背景科技元素 -->
    <!-- <view class="tech-bg">
      <view class="circuit-line"></view>
      <view class="circuit-line reverse"></view>
      <view class="grid-overlay"></view>
    </view> -->

    <!-- 用户信息区 -->
    <view class="user-info">
      <view class="avatar-container">
        <image class="avatar" src="/static/avatar.jpg"></image>
        <view class="avatar-glow"></view>
      </view>
      <view class="user-details">
        <text class="username">lrq</text>
        <text class="user-id">ID: CW2023</text>
      </view>
    </view>

    <!-- VIP卡片 -->
    <view class="vip-card">
      <view class="vip-text">
        <p class="vip-title">CalmWave <text class="vip-badge">PRO</text></p>
        <p class="vip-desc">解锁高级AI心理支持功能</p>
      </view>
      <view class="vip-button-container">
        <button class="vip-button">
          <text>立即升级</text>
          <view class="button-arrow">→</view>
        </button>
      </view>
      <view class="vip-decoration">
        <view class="dot"></view>
        <view class="dot"></view>
        <view class="dot"></view>
      </view>
    </view>

    <!-- 功能菜单 -->
    <view class="menu">
      <navigator url="/pages/update/update" class="menu-item">
        <view class="menu-icon-container">
          <image class="icon" src="/static/contactus.png"></image>
          <view class="icon-glow"></view>
        </view>
        <text>客服中心</text>
        <view class="menu-arrow">›</view>
      </navigator>
      <navigator url="/pages/feedback/feedback" class="menu-item">
        <view class="menu-icon-container">
          <image class="icon" src="/static/yijian.png"></image>
          <view class="icon-glow"></view>
        </view>
        <text>意见反馈</text>
        <view class="menu-arrow">›</view>
      </navigator>
      <navigator url="/pages/about/about" class="menu-item">
        <view class="menu-icon-container">
          <image class="icon" src="/static/aboutUs.png"></image>
          <view class="icon-glow"></view>
        </view>
        <text>关于我们</text>
        <view class="menu-arrow">›</view>
      </navigator>
      <navigator url="/pages/settings/settings" class="menu-item">
        <view class="menu-icon-container">
          <image class="icon" src="/static/setting.png"></image>
          <view class="icon-glow"></view>
        </view>
        <text>设置</text>
        <view class="menu-arrow">›</view>
      </navigator>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const marginTop = ref(0)

onMounted(() => {
  calculateTopHeight()
})

const calculateTopHeight = () => {
  uni.getSystemInfo({
    success: function (res) {
      const menuButtonInfo = uni.getMenuButtonBoundingClientRect()
      const topHeight = menuButtonInfo.top
      marginTop.value = topHeight
    },
  })
}
</script>

<style>
page {
  background: linear-gradient(135deg, #cce5ff,#ffffff );
  color: #2c3e50;
}

.mine-container {
  padding: 30rpx;
  position: relative;
  overflow: hidden;
}

/* 科技背景元素 - 调整为浅色系 */
.tech-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 0;
  opacity: 0.3;
}

.circuit-line {
  position: absolute;
  height: 1px;
  width: 100%;
  background: linear-gradient(90deg, transparent, #3498db, transparent);
  animation: circuitFlow 8s linear infinite;
}

.circuit-line.reverse {
  top: 40%;
  animation: circuitFlowReverse 10s linear infinite;
}

.grid-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    linear-gradient(rgba(52, 152, 219, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(52, 152, 219, 0.05) 1px, transparent 1px);
  background-size: 30px 30px;
}

@keyframes circuitFlow {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@keyframes circuitFlowReverse {
  0% { transform: translateX(100%); }
  100% { transform: translateX(-100%); }
}

/* 用户信息区 */
.user-info {
  display: flex;
  align-items: center;
  padding: 40rpx 30rpx;
  margin-bottom: 30rpx;
  position: relative;
  z-index: 1;
}

.avatar-container {
  position: relative;
  margin-right: 30rpx;
}

.avatar {
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  border: 2px solid rgba(52, 152, 219, 0.5);
  position: relative;
  z-index: 2;
}

.avatar-glow {
  position: absolute;
  width: 160rpx;
  height: 160rpx;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(52, 152, 219, 0.2), transparent 70%);
  top: -10rpx;
  left: -10rpx;
  z-index: 1;
  animation: pulse 3s infinite alternate;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.username {
  font-size: 36rpx;
  font-weight: bold;
  margin-bottom: 10rpx;
  color: #2c3e50;
}

.user-id {
  font-size: 24rpx;
  color: rgba(44, 62, 80, 0.7);
}

/* VIP卡片 - 调整为浅色系 */
.vip-card {
  background: linear-gradient(135deg, #ffffff, #e6f2ff);
  border-radius: 24rpx;
  padding: 40rpx 30rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40rpx;
  position: relative;
  z-index: 1;
  overflow: hidden;
  box-shadow: 0 10rpx 30rpx rgba(52, 152, 219, 0.1);
  border: 1px solid rgba(52, 152, 219, 0.2);
}

.vip-card::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(52, 152, 219, 0.05), transparent 60%);
  z-index: -1;
}

.vip-text {
  flex: 1;
}

.vip-title {
  font-size: 36rpx;
  font-weight: bold;
  margin-bottom: 10rpx;
  display: flex;
  align-items: center;
  color: #2c3e50;
}

.vip-badge {
  background: linear-gradient(90deg, #3498db, #2980b9);
  color: #fff;
  font-size: 24rpx;
  padding: 4rpx 12rpx;
  border-radius: 20rpx;
  margin-left: 15rpx;
  font-weight: bold;
}

.vip-desc {
  font-size: 26rpx;
  color: rgba(44, 62, 80, 0.8);
}

.vip-button-container {
  width: 300rpx;
}

.vip-button {
  background: linear-gradient(90deg, #3498db, #2980b9);
  color: #fff;
  border: none;
  border-radius: 50rpx;
  padding: 16rpx 0;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 5rpx 15rpx rgba(52, 152, 219, 0.2);
  transition: all 0.3s;
}

.vip-button:active {
  transform: scale(0.95);
}

.button-arrow {
  margin-left: 10rpx;
  font-weight: bold;
  font-size: 32rpx;
  color: #fff;
}

.vip-decoration {
  position: absolute;
  bottom: 10rpx;
  right: 20rpx;
  display: flex;
}

.dot {
  width: 8rpx;
  height: 8rpx;
  background-color: rgba(52, 152, 219, 0.5);
  border-radius: 50%;
  margin-right: 8rpx;
}

/* 功能菜单 - 调整为浅色系 */
.menu {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 24rpx;
  padding: 0 30rpx;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(52, 152, 219, 0.2);
  position: relative;
  z-index: 1;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 35rpx 0;
  position: relative;
  border-bottom: 1px solid rgba(52, 152, 219, 0.1);
  color: #2c3e50;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-icon-container {
  position: relative;
  margin-right: 25rpx;
}

.icon {
  width: 50rpx;
  height: 50rpx;
  z-index: 2;
  position: relative;
}

.icon-glow {
  position: absolute;
  width: 70rpx;
  height: 70rpx;
  border-radius: 50%;
  background: rgba(52, 152, 219, 0.1);
  top: -10rpx;
  left: -10rpx;
  z-index: 1;
}

.menu-arrow {
  margin-left: auto;
  color: #3498db;
  font-size: 40rpx;
}

/* 动画效果 */
@keyframes pulse {
  0% { opacity: 0.3; transform: scale(0.95); }
  100% { opacity: 0.6; transform: scale(1.05); }
}

/* 悬停效果 */
.menu-item:active {
  background: rgba(52, 152, 219, 0.05);
}
</style>