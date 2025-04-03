<template>
  <view class="ec-canvas">
    <canvas
      :canvas-id="canvasId"
      :id="canvasId"
      type="2d"
      :style="canvasStyle"
      @touchstart="touchStart"
      @touchmove="touchMove"
      @touchend="touchEnd"
    ></canvas>
  </view>
</template>

<script>
import * as echarts from 'echarts'

export default {
  props: {
    canvasId: {
      type: String,
      default: 'ec-canvas',
    },
    ec: {
      type: Object,
      default: () => ({}),
    },
    width: {
      type: [String, Number],
      default: '100%',
    },
    height: {
      type: [String, Number],
      default: '500rpx',
    },
  },

  data() {
    return {
      chart: null,
      canvasStyle: `width: ${this.width}; height: ${this.height};`,
    }
  },

  mounted() {
    this.init()
  },

  methods: {
    init(callback) {
      return new Promise((resolve) => {
        const query = uni.createSelectorQuery().in(this.$parent)
        query
          .select(`#${this.canvasId}`)
          .fields({ node: true, size: true })
          .exec((res) => {
            if (!res || !res[0] || !res[0].node) {
              console.error('获取Canvas节点失败')
              return resolve(null)
            }

            const canvas = res[0].node
            const dpr = uni.getSystemInfoSync().pixelRatio
            const width = res[0].width
            const height = res[0].height

            canvas.width = width * dpr
            canvas.height = height * dpr

            const chart = echarts.init(canvas, null, {
              width: width,
              height: height,
              devicePixelRatio: dpr,
            })

            if (typeof callback === 'function') {
              callback(chart, canvas, width, height)
            }

            resolve(chart)
          })
      })
    },

    initByNewWay(callback) {
      const query = uni.createSelectorQuery().in(this)
      query
        .select(`#${this.canvasId}`)
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res[0]) return

          const canvasNode = res[0].node
          const canvasDpr = uni.getSystemInfoSync().pixelRatio
          const canvasWidth = res[0].width
          const canvasHeight = res[0].height

          canvasNode.width = canvasWidth * canvasDpr
          canvasNode.height = canvasHeight * canvasDpr

          this.chart = echarts.init(canvasNode, null, {
            width: canvasWidth,
            height: canvasHeight,
            devicePixelRatio: canvasDpr,
          })

          if (typeof callback === 'function') {
            callback(this.chart, canvasNode, canvasWidth, canvasHeight)
          }
        })
    },

    canvasToTempFilePath(opt) {
      const { canvasId } = this
      return new Promise((resolve) => {
        uni.canvasToTempFilePath(
          {
            canvasId,
            ...opt,
            success: resolve,
            fail: resolve,
          },
          this,
        )
      })
    },

    touchStart(e) {
      if (this.chart && e.touches.length > 0) {
        const touch = e.touches[0]
        this.chart._zr.handler.dispatch('mousedown', {
          zrX: touch.x,
          zrY: touch.y,
        })
      }
    },

    touchMove(e) {
      if (this.chart && e.touches.length > 0) {
        const touch = e.touches[0]
        this.chart._zr.handler.dispatch('mousemove', {
          zrX: touch.x,
          zrY: touch.y,
        })
      }
    },

    touchEnd() {
      if (this.chart) {
        this.chart._zr.handler.dispatch('mouseup')
      }
    },
  },
}
</script>

<style>
.ec-canvas {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
