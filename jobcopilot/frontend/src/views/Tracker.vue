<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listApplications, updateApplication, deleteApplication, createApplication, getTrackerStats } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProgressBar from '@/components/ProgressBar.vue'
import EmptyState from '@/components/EmptyState.vue'

const applications = ref<any[]>([])
const loading = ref(false)
const stats = ref<any>({ total: 0, by_status: {}, avg_match_score: 0 })
const dialogVisible = ref(false)
const form = ref({ company_name: '', position_title: '', jd_text: '', status: '待投递' })

const statusOrder = ['待投递', '已投递', '初筛中', '面试中', '已发Offer', '已拒绝']
const statusFilter = ref('')
const filters = ['全部', ...statusOrder]

function selectFilter(f: string) {
  statusFilter.value = f === '全部' ? '' : f
  fetchData()
}

async function fetchData() {
  loading.value = true
  try {
    const data: any = await listApplications(statusFilter.value || undefined)
    applications.value = data
    const s: any = await getTrackerStats()
    stats.value = s
  } catch { ElMessage.error('获取数据失败') }
  finally { loading.value = false }
}

async function handleStatusChange(row: any) {
  try {
    await updateApplication(row.id, { status: row.status })
    ElMessage.success('状态已更新')
    fetchData()
  } catch { ElMessage.error('更新失败') }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此记录？', '确认', { type: 'warning' })
    await deleteApplication(id)
    ElMessage.success('已删除')
    fetchData()
  } catch { /* user cancelled */ }
}

async function handleCreate() {
  try {
    await createApplication(form.value)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    form.value = { company_name: '', position_title: '', jd_text: '', status: '待投递' }
    fetchData()
  } catch { ElMessage.error('创建失败') }
}

onMounted(fetchData)
</script>

<template>
  <div class="tracker-page">
    <div class="tracker-header">
      <div>
        <h2 class="page-title">投递进度管理</h2>
        <p class="page-sub">共 {{ stats.total }} 条记录 · 平均匹配度 {{ stats.avg_match_score }}</p>
      </div>
    </div>

    <!-- Kanban pipe -->
    <div class="tracker-kanban" v-if="stats.total > 0">
      <div class="pipe-header">
        <div>
          <span class="pipe-total">{{ stats.total }}</span>
          <span class="pipe-unit">条记录</span>
        </div>
        <div class="pipe-avg">
          平均匹配度 <span class="pipe-score">{{ stats.avg_match_score }}</span>
        </div>
      </div>
      <div class="pipe-bar">
        <div
          v-for="status in statusOrder"
          :key="status"
          class="pipe-seg"
          :style="{ flex: (stats.by_status?.[status] || 0) || 0.3 }"
        ></div>
      </div>
      <div class="pipe-labels">
        <span v-for="status in statusOrder" :key="status" class="pipe-label">
          {{ status }} <strong>{{ stats.by_status?.[status] || 0 }}</strong>
        </span>
      </div>
    </div>

    <!-- Pill filters -->
    <div class="pill-filters">
      <button
        v-for="f in filters"
        :key="f"
        class="pill"
        :class="{ active: (f === '全部' ? '' : f) === statusFilter }"
        @click="selectFilter(f)"
      >{{ f }}</button>
    </div>

    <!-- Table -->
    <div v-if="applications.length > 0" class="table-wrap">
      <el-table :data="applications" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="company_name" label="公司" min-width="150" />
        <el-table-column prop="position_title" label="职位" min-width="150" />
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-select v-model="row.status" size="small" @change="handleStatusChange(row)" style="width: 110px">
              <el-option v-for="s in statusOrder" :key="s" :label="s" :value="s" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="匹配度" width="120">
          <template #default="{ row }">
            <ProgressBar v-if="row.match_score !== null && row.match_score !== undefined" :value="row.match_score" />
            <span v-else style="color: var(--text-muted)">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">{{ row.updated_at?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="danger" text @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <EmptyState
      v-else-if="!loading"
      title="还没有投递记录"
      description="点击右下角 + 按钮开始记录第一份投递"
      action-label="立即添加"
      @action="dialogVisible = true"
    />

    <!-- FAB -->
    <button class="fab" @click="dialogVisible = true" title="新增投递">
      <el-icon :size="24"><Plus /></el-icon>
    </button>

    <!-- Create dialog -->
    <el-dialog v-model="dialogVisible" title="新增投递记录" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="公司名称">
          <el-input v-model="form.company_name" placeholder="例如：字节跳动" />
        </el-form-item>
        <el-form-item label="职位名称">
          <el-input v-model="form.position_title" placeholder="例如：AI 产品经理" />
        </el-form-item>
        <el-form-item label="JD文本">
          <el-input v-model="form.jd_text" type="textarea" :rows="4" placeholder="可选，粘贴职位描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tracker-page {
  position: relative;
  min-height: calc(100vh - 48px);
}

.page-title { margin-bottom: 4px; }
.page-sub { font-size: 13px; color: var(--text-muted); }

.tracker-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

/* Kanban pipe */
.tracker-kanban {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 20px;
  margin-bottom: 16px;
}

.pipe-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 14px;
  color: var(--text-secondary);
  font-size: 13px;
}

.pipe-total { font-size: 32px; font-weight: 700; color: var(--text-primary); margin-right: 8px; }
.pipe-unit { color: var(--text-muted); }
.pipe-score { color: var(--accent); font-weight: 600; }

.pipe-bar {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  gap: 2px;
  margin-bottom: 12px;
}

.pipe-seg {
  background: rgba(240, 185, 11, 0.3);
  border-radius: 2px;
  transition: flex var(--t-normal) ease;
}

.pipe-seg:first-child { background: rgba(240, 185, 11, 0.5); }
.pipe-seg:last-child { background: rgba(240, 185, 11, 0.1); }

.pipe-labels { display: flex; justify-content: space-between; }
.pipe-label { font-size: 12px; color: var(--text-muted); }
.pipe-label strong { color: var(--text-secondary); font-weight: 600; }

/* Pill filters */
.pill-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pill {
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid var(--border-input);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--t-fast) ease-out;
}

.pill:hover { border-color: var(--text-muted); color: var(--text-primary); }

.pill.active {
  background: var(--accent);
  color: #ffffff;
  border-color: var(--accent);
  font-weight: 600;
}

/* Table */
.table-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  overflow: hidden;
}

/* FAB */
.fab {
  position: fixed;
  bottom: 32px;
  right: 32px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--accent);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(240, 185, 11, 0.3);
  transition: all var(--t-fast) ease-out;
  z-index: 100;
}

.fab:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 28px rgba(240, 185, 11, 0.45);
}

.fab:active { transform: scale(0.95); }
</style>
