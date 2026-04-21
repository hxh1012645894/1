<template>
  <div class="upload-container">
    <h2>批量上传批件及通知书</h2>
    <el-alert
      title="请上传 PDF 或 JPG/PNG 扫描件，系统将自动进行拆分、OCR及智能提取。"
      type="info"
      show-icon
      style="margin-bottom: 20px;"
    />

    <el-upload
      class="upload-demo"
      drag
      multiple
      :auto-upload="false"
      ref="uploadRef"
      action="#"
      :file-list="fileList"
      @change="handleChange"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">将文件拖到此处，或 <em>点击上传</em></div>
    </el-upload>

    <div style="margin-top: 20px;">
      <el-button
        type="primary"
        @click="submitUpload"
        :loading="isProcessing"
      >
        开始智能解析并入库
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

const uploadRef = ref(null)
const fileList = ref([])
const isProcessing = ref(false)
const router = useRouter()

const handleChange = (file, files) => {
  fileList.value = files
}

const submitUpload = async () => {
  if (fileList.value.length === 0) {
    return ElMessage.warning('请先选择文件')
  }

  isProcessing.value = true
  const formData = new FormData()
  fileList.value.forEach(item => formData.append('files', item.raw))

  try {
    const res = await axios.post('http://localhost:8001/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    // 后台处理中，等 WebSocket 通知或手动切台账页查看
    ElMessage.success(`文件已接收，正在后台解析处理中...`)
    fileList.value = [] // 清空列表
  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error('解析失败，请检查后端服务。')
  } finally {
    isProcessing.value = false
  }
}
</script>

<style scoped>
.upload-container {
  padding: 20px;
}
.el-upload {
  margin-top: 20px;
}
</style>
