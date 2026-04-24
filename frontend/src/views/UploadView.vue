<template>
  <div class="upload-container">
    <h2>批量上传批件及通知书</h2>
    <el-alert
      title="请上传 PDF 或 JPG/PNG 扫描件。支持智能解析提取信息，或直接作为纯附件归档。"
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

    <div class="action-buttons">
      <el-button
        type="primary"
        @click="submitUpload('smart')"
        :loading="isProcessing"
      >
        开始智能解析并入库
      </el-button>

      <el-button
        type="success"
        @click="submitUpload('attachment_only')"
        :loading="isProcessing"
      >
        仅作为附件直接入库（不解析）
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

const submitUpload = async (uploadType) => {
  if (fileList.value.length === 0) {
    return ElMessage.warning('请先选择文件')
  }

  isProcessing.value = true
  const formData = new FormData()
  fileList.value.forEach(item => formData.append('files', item.raw))

  // 核心：把上传类型传给后端
  formData.append('upload_type', uploadType)

  try {
    const res = await axios.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    // 根据不同类型给用户不同的提示
    if (uploadType === 'smart') {
      ElMessage.success('文件已接收，正在后台智能解析处理中...')
    } else {
      ElMessage.success('附件已快速入库完成！')
    }

    fileList.value = [] // 清空列表
  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error('处理失败，请检查后端服务。')
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
.action-buttons {
  margin-top: 20px;
  display: flex;
  gap: 15px;
}
</style>