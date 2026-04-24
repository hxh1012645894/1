<template>
  <div class="records-container">
    <h2>药品注册批件台账</h2>

    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-title">总文件数</div>
          <div class="stat-value" style="color: #409EFF;">{{ loading ? '...' : stats.totalFiles }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-title">产品总数</div>
          <div class="stat-value" style="color: #67C23A;">{{ loading ? '...' : stats.totalProducts }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-title">即将到期批件 (一年内)</div>
          <div class="stat-value" style="color: #E6A23C;">{{ loading ? '...' : stats.expiringSoon }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-title">已过期批件</div>
          <div class="stat-value" style="color: #F56C6C;">{{ loading ? '...' : stats.expired }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索框 -->
    <el-row :gutter="20" class="search-row" v-if="hasData || searchKeyword">
      <el-col :span="6">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索批件号、受理号、药品名称"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #append>
            <el-button icon="Search" @click="handleSearch">搜索</el-button>
          </template>
        </el-input>
      </el-col>
      <el-col :span="6">
        <el-select v-model="sortBy" placeholder="排序字段" @change="handleSortChange">
          <el-option label="默认排序" value="id" />
          <el-option label="批准日期" value="approval_date" />
          <el-option label="到期时间" value="expiry_date" />
          <el-option label="申请时间" value="apply_time" />
        </el-select>
      </el-col>
      <el-col :span="4">
        <el-select v-model="sortOrder" placeholder="排序方向" @change="handleSortChange">
          <el-option label="降序 (最新)" value="desc" />
          <el-option label="升序 (最早)" value="asc" />
        </el-select>
      </el-col>
    </el-row>

    <!-- 空数据提示 -->
    <div v-if="!loading && !hasData" class="empty-state">
      <el-empty description="暂无批件数据，正在解析中..." :image-size="100">
        <template #description>
          <div>正在解析批件数据，请耐心等待...</div>
          <div class="empty-hint">数据解析完成后将自动显示</div>
        </template>
      </el-empty>
    </div>

    <el-table
      :data="records"
      border
      stripe
      style="width: 100%"
      v-loading="loading"
      empty-text="暂无批件数据"
      :class="{ 'hidden-table': !hasData && !loading }"
      @expand-change="handleExpand"
    >
      <el-table-column type="expand">
        <template #default="props">
          <div class="expand-detail">
            <el-descriptions title="批件详细信息" :column="2" border>
              <el-descriptions-item label="申请人">{{ props.row.applicant }}</el-descriptions-item>
              <el-descriptions-item label="生产企业">{{ props.row.enterprise }}</el-descriptions-item>
              <el-descriptions-item label="生产地址">{{ props.row.address }}</el-descriptions-item>
              <el-descriptions-item label="上市许可持有人">{{ props.row.owner }}</el-descriptions-item>
              <el-descriptions-item label="申请号">{{ props.row.application_no }}</el-descriptions-item>
              <el-descriptions-item label="药品批准文号">{{ props.row.drug_approval_no }}</el-descriptions-item>
              <el-descriptions-item label="药品标准编号">{{ props.row.drug_standard_no }}</el-descriptions-item>
              <el-descriptions-item label="申请时间">{{ props.row.apply_time }}</el-descriptions-item>
              <el-descriptions-item label="受理时间">{{ props.row.handle_time }}</el-descriptions-item>
              <el-descriptions-item label="审批结论" :span="2">
                <div>
                  <span>{{ getFirstSentence(props.row.conclusion) }}</span>
                  <el-tooltip v-if="props.row.conclusion && props.row.conclusion.length > 50" placement="top">
                    <template #content>
                      <div style="white-space: pre-wrap; max-width: 400px;">{{ props.row.conclusion }}</div>
                    </template>
                    <el-link type="primary" style="font-size: 12px; margin-left: 8px;">查看全部</el-link>
                  </el-tooltip>
                </div>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="approval_no" label="批件号" min-width="110" show-overflow-tooltip></el-table-column>
      <el-table-column prop="handle_no" label="受理号" min-width="110" show-overflow-tooltip></el-table-column>
      <el-table-column prop="product_name" label="药品名称" min-width="130" show-overflow-tooltip></el-table-column>
      <el-table-column prop="dosage" label="剂型" min-width="80" show-overflow-tooltip></el-table-column>
      <el-table-column prop="specification" label="规格" min-width="100" show-overflow-tooltip></el-table-column>
      <el-table-column prop="registration_class" label="注册/药品分类" min-width="100" show-overflow-tooltip></el-table-column>
      <el-table-column prop="application" label="申请事项" min-width="110" show-overflow-tooltip></el-table-column>
      <el-table-column prop="approval_date" label="批准日期" min-width="100"></el-table-column>
      <el-table-column prop="validity" label="有效期" min-width="80"></el-table-column>
      <el-table-column prop="expiry_date" label="到期时间" min-width="100"></el-table-column>
      <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip></el-table-column>

      <el-table-column label="操作" fixed="right" width="350">
        <template #default="scope">
          <el-button
            size="small"
            type="primary"
            @click="previewPdf(scope.row.main_file_path, '批件预览')"
          >
            查看批件
          </el-button>
          <el-button
            size="small"
            type="success"
            :disabled="!scope.row.attach_file_path"
            @click="previewPdf(scope.row.attach_file_path, '附件预览')"
          >
            查看附件
          </el-button>
          <el-button
            size="small"
            type="warning"
            @click="editRecord(scope.row, scope.$index)"
          >
            修改
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click="deleteRecord(scope.row.id, scope.$index)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页组件 -->
    <el-row justify="end" class="pagination-row" v-if="hasData">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="totalRecords"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </el-row>

    <!-- 修改对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="修改批件信息"
      width="800px"
    >
      <el-form :model="editForm" label-width="100px" size="small">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="产品名称">
              <el-input v-model="editForm.product_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="批件号">
              <el-input v-model="editForm.approval_no" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="受理号">
              <el-input v-model="editForm.handle_no" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="剂型">
              <el-input v-model="editForm.dosage" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="规格">
              <el-input v-model="editForm.specification" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="注册/药品分类">
              <el-input v-model="editForm.registration_class" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="申请事项">
              <el-input v-model="editForm.application" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="批准日期">
              <el-input v-model="editForm.approval_date" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="有效期">
              <el-input v-model="editForm.validity" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="到期时间">
              <el-input v-model="editForm.expiry_date" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="申请人">
          <el-input v-model="editForm.applicant" />
        </el-form-item>
        <el-form-item label="生产企业">
          <el-input v-model="editForm.enterprise" />
        </el-form-item>
        <el-form-item label="生产地址">
          <el-input v-model="editForm.address" />
        </el-form-item>
        <el-form-item label="上市许可持有人">
          <el-input v-model="editForm.owner" />
        </el-form-item>
        <el-form-item label="申请号">
          <el-input v-model="editForm.application_no" />
        </el-form-item>
        <el-form-item label="药品批准文号">
          <el-input v-model="editForm.drug_approval_no" />
        </el-form-item>
        <el-form-item label="药品标准编号">
          <el-input v-model="editForm.drug_standard_no" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="申请时间">
              <el-input v-model="editForm.apply_time" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="受理时间">
              <el-input v-model="editForm.handle_time" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="审批结论">
          <el-input v-model="editForm.conclusion" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="70%"
      top="5vh"
    >
      <iframe :src="pdfUrl" width="100%" height="600px" frameborder="0"></iframe>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const records = ref([])
const loading = ref(false)
const hasData = ref(false)

// 搜索和分页
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalRecords = ref(0)

// 排序
const sortBy = ref('id')
const sortOrder = ref('desc')

// 展开状态追踪
const isAnyRowExpanded = ref(false)

const stats = ref({
  totalFiles: 0,
  totalProducts: 0,
  expiringSoon: 0,
  expired: 0
})

const dialogVisible = ref(false)
const dialogTitle = ref('')
const pdfUrl = ref('')

// 编辑相关
const editDialogVisible = ref(false)
const editForm = ref({})
const currentIndex = ref(0)

// 修改：增加 silent 参数，如果是静默刷新则不显示 loading 动画
const fetchRecords = async (silent = false) => {
  if (!silent) loading.value = true
  try {
    const res = await axios.get('/api/records', {
      params: {
        search: searchKeyword.value,
        page: currentPage.value,
        size: pageSize.value,
        sort_by: sortBy.value,
        sort_order: sortOrder.value
      }
    })
    records.value = res.data.records
    totalRecords.value = res.data.total

    // 统计数据单独获取（不受分页影响）
    const statsRes = await axios.get('/api/stats')
    stats.value = statsRes.data
    hasData.value = statsRes.data.totalFiles > 0
  } catch (error) {
    console.error("获取数据失败", error)
  } finally {
    if (!silent) loading.value = false
  }
}

// 搜索处理
const handleSearch = () => {
  currentPage.value = 1  // 搜索时重置到第一页
  fetchRecords()
}

// 排序变化处理
const handleSortChange = () => {
  currentPage.value = 1  // 排序时重置到第一页
  fetchRecords()
}

// 分页大小变化
const handleSizeChange = () => {
  currentPage.value = 1  // 改变每页条数时重置到第一页
  fetchRecords()
}

// 页码变化
const handlePageChange = () => {
  fetchRecords()
}

// 展开状态处理
const handleExpand = (row, expandedRows) => {
  isAnyRowExpanded.value = expandedRows.length > 0

  if (isAnyRowExpanded.value) {
    // 有展开的行，暂停轮询
    stopPolling()
  } else {
    // 全部折叠，刷新一次并恢复轮询
    fetchRecords(true)
    startPolling()
  }
}

// 轮询控制
let pollTimer = null

const startPolling = () => {
  if (pollTimer) return
  pollTimer = setInterval(() => {
    if (!isAnyRowExpanded.value) {
      fetchRecords(true)
    }
  }, 10000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const previewPdf = (filePath, title) => {
  if (!filePath) return
  pdfUrl.value = `/api/preview?path=${encodeURIComponent(filePath)}`
  dialogTitle.value = title
  dialogVisible.value = true
}

// 获取审批结论的第一句话
const getFirstSentence = (text) => {
  if (!text || text === 'N/A') return text
  // 匹配句子结束符（。！？；）或换行符
  const match = text.match(/^([^。！？；\n]+[。！？；])|^(.+)/)
  if (match) {
    return (match[1] || match[2] || '').trim()
  }
  return text.trim()
}

const deleteRecord = async (recordId, rowIndex) => {
  try {
    // 删除前确认
    await ElMessageBox.confirm('确定要删除此记录吗？此操作不可恢复。', '删除确认', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })

    await axios.delete(`/api/records/${recordId}`)
    fetchRecords(true)  // 刷新数据
    ElMessage.success('删除成功')
  } catch (error) {
    // 用户取消删除或发生错误
    if (error !== 'cancel') {
      console.error("删除失败", error)
      ElMessage.error('删除失败')
    }
  }
}

const editRecord = (record, rowIndex) => {
  currentIndex.value = rowIndex
  editForm.value = { ...record }
  editDialogVisible.value = true
}

const saveEdit = async () => {
  try {
    await axios.put(`/api/records/${editForm.value.id}`, editForm.value)
    fetchRecords(true)  // 刷新数据
    ElMessage.success('修改成功')
    editDialogVisible.value = false
  } catch (error) {
    console.error("修改失败", error)
    ElMessage.error('修改失败')
  }
}

onMounted(() => {
  // 首次加载带 loading 动画
  fetchRecords()
  // 开启定时轮询
  startPolling()
})

onUnmounted(() => {
  // 页面卸载时清除定时器
  stopPolling()
})
</script>

<style scoped>
.records-container {
  padding: 20px;
}
.expand-detail {
  padding: 20px;
  background-color: #fafafa;
}
/* 统计卡片样式 */
.stat-cards {
  margin-bottom: 25px;
}
.stat-card {
  text-align: center;
  border-radius: 8px;
}
.stat-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}
.stat-value {
  font-size: 28px;
  font-weight: bold;
}
/* 搜索框样式 */
.search-row {
  margin-bottom: 20px;
}
/* 分页样式 */
.pagination-row {
  margin-top: 20px;
}
/* 空数据状态样式 */
.empty-state {
  margin-top: 50px;
  text-align: center;
}
.empty-hint {
  color: #909399;
  font-size: 14px;
  margin-top: 8px;
}
/* 隐藏表格样式 */
.hidden-table {
  display: none;
}
</style>
