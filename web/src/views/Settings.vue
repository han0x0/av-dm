<template>
  <div class="settings-page">
    <!-- 服务连接配置对话框 -->
    <el-dialog
      v-model="servicesDialogVisible"
      title="服务连接配置"
      width="700px"
      :close-on-click-modal="false"
      class="services-dialog"
    >
      <el-tabs v-model="activeServiceTab" type="border-card">
        <!-- FreshRSS -->
        <el-tab-pane label="FreshRSS" name="freshrss">
          <el-form :model="editForm" label-width="150px">
            <el-form-item label="服务地址">
              <el-input v-model="editForm.freshrss_url" placeholder="https://rss.your-domain.com" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="editForm.freshrss_username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input 
                v-model="editForm.freshrss_password" 
                :type="passwordVisible.freshrss ? 'text' : 'password'"
                :placeholder="passwordConfigured.freshrss ? '已配置（留空保持不变）' : '请输入密码'"
              >
                <template #suffix>
                  <el-icon @click="passwordVisible.freshrss = !passwordVisible.freshrss" class="password-eye">
                    <View v-if="passwordVisible.freshrss" />
                    <Hide v-else />
                  </el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-button 
                type="primary" 
                @click="testService('freshrss')"
                :loading="testingServices.freshrss"
              >
                <el-icon><Connection /></el-icon> 测试连接
              </el-button>
              <el-button 
                type="success" 
                @click="saveSingleServiceConfig('freshrss')"
                :loading="saving"
              >
                <el-icon><Check /></el-icon> 保存 FreshRSS 配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- RSSHub -->
        <el-tab-pane label="RSSHub" name="rsshub">
          <el-form :model="editForm" label-width="150px">
            <el-form-item label="服务地址">
              <el-input v-model="editForm.rsshub_base_url" placeholder="https://rsshub.your-domain.com" />
            </el-form-item>
            <el-form-item>
              <el-button 
                type="primary" 
                @click="testService('rsshub')"
                :loading="testingServices.rsshub"
              >
                <el-icon><Connection /></el-icon> 测试连接
              </el-button>
              <el-button 
                type="success" 
                @click="saveSingleServiceConfig('rsshub')"
                :loading="saving"
              >
                <el-icon><Check /></el-icon> 保存 RSSHub 配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- BitComet -->
        <el-tab-pane label="BitComet" name="bitcomet">
          <el-form :model="editForm" label-width="180px">
            <el-form-item label="服务地址">
              <el-input v-model="editForm.bitcomet_url" placeholder="https://bit.your-domain.com:8888" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="editForm.bitcomet_username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input 
                v-model="editForm.bitcomet_password" 
                :type="passwordVisible.bitcomet ? 'text' : 'password'"
                :placeholder="passwordConfigured.bitcomet ? '已配置（留空保持不变）' : '请输入密码'"
              >
                <template #suffix>
                  <el-icon @click="passwordVisible.bitcomet = !passwordVisible.bitcomet" class="password-eye">
                    <View v-if="passwordVisible.bitcomet" />
                    <Hide v-else />
                  </el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-divider content-position="left">认证信息（抓包获取）</el-divider>
            <el-form-item label="Client ID">
              <el-input v-model="editForm.bitcomet_client_id" placeholder="可选，默认使用内置值" />
            </el-form-item>
            <el-form-item label="Authentication">
              <el-input 
                v-model="editForm.bitcomet_authentication" 
                :type="passwordVisible.bitcomet_auth ? 'textarea' : 'password'"
                :rows="passwordVisible.bitcomet_auth ? 3 : 1"
                :placeholder="passwordConfigured.bitcomet_auth ? '已配置（留空保持不变）' : '从浏览器 DevTools 抓包获取'"
              />
              <div class="form-hint">
                <el-icon><InfoFilled /></el-icon>
                在 BitComet WebUI 登录时，按 F12 → Network → 找到 /api/webui/login 请求 → 复制 authentication 字段
              </div>
            </el-form-item>
            <el-form-item>
              <el-button 
                type="primary" 
                @click="testService('bitcomet')"
                :loading="testingServices.bitcomet"
              >
                <el-icon><Connection /></el-icon> 测试连接
              </el-button>
              <el-button 
                type="success" 
                @click="saveSingleServiceConfig('bitcomet')"
                :loading="saving"
              >
                <el-icon><Check /></el-icon> 保存 BitComet 配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- JavSP -->
        <el-tab-pane label="JavSP-Web" name="javsp">
          <el-form :model="editForm" label-width="150px">
            <el-form-item label="服务地址">
              <el-input v-model="editForm.javsp_url" placeholder="http://javsp-web:8090" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="editForm.javsp_username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input 
                v-model="editForm.javsp_password" 
                :type="passwordVisible.javsp ? 'text' : 'password'"
                :placeholder="passwordConfigured.javsp ? '已配置（留空保持不变）' : '请输入密码'"
              >
                <template #suffix>
                  <el-icon @click="passwordVisible.javsp = !passwordVisible.javsp" class="password-eye">
                    <View v-if="passwordVisible.javsp" />
                    <Hide v-else />
                  </el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-button 
                type="primary" 
                @click="testService('javsp')"
                :loading="testingServices.javsp"
              >
                <el-icon><Connection /></el-icon> 测试连接
              </el-button>
              <el-button 
                type="success" 
                @click="saveSingleServiceConfig('javsp')"
                :loading="saving"
              >
                <el-icon><Check /></el-icon> 保存 JavSP 配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- Jellyfin -->
        <el-tab-pane label="Jellyfin" name="jellyfin">
          <el-form :model="editForm" label-width="150px">
            <el-form-item label="服务地址">
              <el-input v-model="editForm.jellyfin_url" placeholder="https://jellyfin.your-domain.com" />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input 
                v-model="editForm.jellyfin_api_key" 
                :type="passwordVisible.jellyfin ? 'text' : 'password'"
                :placeholder="passwordConfigured.jellyfin ? '已配置（留空保持不变）' : '请输入 API Key'"
              >
                <template #suffix>
                  <el-icon @click="passwordVisible.jellyfin = !passwordVisible.jellyfin" class="password-eye">
                    <View v-if="passwordVisible.jellyfin" />
                    <Hide v-else />
                  </el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="媒体库名称">
              <el-input v-model="editForm.jellyfin_library_name" placeholder="video" />
            </el-form-item>
            <el-form-item>
              <el-button 
                type="primary" 
                @click="testService('jellyfin')"
                :loading="testingServices.jellyfin"
              >
                <el-icon><Connection /></el-icon> 测试连接
              </el-button>
              <el-button 
                type="success" 
                @click="saveSingleServiceConfig('jellyfin')"
                :loading="saving"
              >
                <el-icon><Check /></el-icon> 保存 Jellyfin 配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="servicesDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveAllServicesConfig" :loading="saving">保存全部</el-button>
      </template>
    </el-dialog>

    <!-- 业务配置对话框 -->
    <el-dialog
      v-model="businessDialogVisible"
      title="业务配置"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="editForm" label-width="200px">
        <el-divider>工作流调度（分钟）</el-divider>
        <el-form-item label="Workflow 1 间隔">
          <el-input-number v-model="editForm.workflow1_interval_minutes" :min="1" :max="1440" />
          <span class="form-hint">处理 Starred Items</span>
        </el-form-item>
        <el-form-item label="Workflow 2 间隔">
          <el-input-number v-model="editForm.workflow2_interval_minutes" :min="1" :max="1440" />
          <span class="form-hint">状态监控</span>
        </el-form-item>
        <el-form-item label="Workflow 3 间隔">
          <el-input-number v-model="editForm.workflow3_interval_minutes" :min="1" :max="1440" />
          <span class="form-hint">空间管理与清理</span>
        </el-form-item>
        
        <el-divider>JavSP 提交条件</el-divider>
        <el-form-item label="分享率阈值">
          <el-input-number v-model="editForm.javsp_submit_share_ratio" :min="0" :max="10" :precision="1" :step="0.1" />
          <span class="form-hint">下载完成且分享率超过此值则提交（如 2.0 = 200%）</span>
        </el-form-item>
        <el-form-item label="创建时间阈值">
          <el-input-number v-model="editForm.javsp_submit_hours" :min="0" :max="168" :precision="1" :step="0.5" />
          <span class="form-hint">下载完成且创建时间超过此值则提交（小时）</span>
        </el-form-item>
        
        <el-divider>业务参数</el-divider>
        <el-form-item label="最大保留完成数">
          <el-input-number v-model="editForm.max_completed_downloads" :min="10" :max="500" />
          <span class="form-hint">Jellyfin 媒体库最大保留影片数量</span>
        </el-form-item>
        <el-form-item label="最大重试次数">
          <el-input-number v-model="editForm.max_retry_count" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="重试延迟">
          <el-input-number v-model="editForm.retry_delay_seconds" :min="10" :max="600" />
          <span class="form-hint">秒</span>
        </el-form-item>
        <el-form-item label="下载超时时间">
          <el-input-number v-model="editForm.download_timeout_hours" :min="1" :max="168" />
          <span class="form-hint">超过此时间未完成则标记为 timeout（小时）</span>
        </el-form-item>

        <el-divider>路径配置</el-divider>
        <el-form-item label="BitComet 下载路径">
          <el-input v-model="editForm.bitcomet_download_path" />
        </el-form-item>
        <el-form-item label="JavSP 输入路径">
          <el-input v-model="editForm.javsp_input_path" />
        </el-form-item>
        <el-form-item label="JavSP 输出路径">
          <el-input v-model="editForm.javsp_output_path" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="businessDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveBusinessConfig" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- Web UI 配置对话框 -->
    <el-dialog
      v-model="webuiDialogVisible"
      title="Web UI 配置"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="editForm" label-width="120px">
        <el-form-item label="登录密码">
          <el-input 
            v-model="editForm.web_password" 
            :type="passwordVisible.webui ? 'text' : 'password'"
            :placeholder="config?.web_password_configured ? '已配置（留空保持不变）' : '请输入密码'"
          >
            <template #suffix>
              <el-icon @click="passwordVisible.webui = !passwordVisible.webui" class="password-eye">
                <View v-if="passwordVisible.webui" />
                <Hide v-else />
              </el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="JWT 密钥">
          <el-input 
            v-model="editForm.web_secret_key" 
            :type="passwordVisible.webui_key ? 'text' : 'password'"
            :placeholder="'用于生成登录令牌，建议修改为随机字符串'"
          >
            <template #suffix>
              <el-icon @click="passwordVisible.webui_key = !passwordVisible.webui_key" class="password-eye">
                <View v-if="passwordVisible.webui_key" />
                <Hide v-else />
              </el-icon>
            </template>
          </el-input>
          <div class="form-hint">用于生成登录令牌，建议修改为随机字符串</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="webuiDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveWebUIConfig" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 备份管理对话框 -->
    <el-dialog
      v-model="backupDialogVisible"
      title="配置备份管理"
      width="700px"
    >
      <div class="backup-actions">
        <el-button type="primary" @click="createBackup" :loading="creatingBackup">
          <el-icon><Plus /></el-icon> 创建备份
        </el-button>
        <el-button @click="fetchBackups">
          <el-icon><Refresh /></el-icon> 刷新列表
        </el-button>
      </div>
      
      <el-table :data="backups" v-loading="loadingBackups" style="margin-top: 16px;">
        <el-table-column prop="name" label="备份文件名" min-width="200" />
        <el-table-column prop="created" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created) }}
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="restoreBackup(row.name)" :loading="restoring === row.name">
              恢复
            </el-button>
            <el-button type="danger" size="small" @click="deleteBackup(row.name)" :loading="deleting === row.name">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-empty v-if="backups.length === 0 && !loadingBackups" description="暂无备份" />
    </el-dialog>

    <!-- 页面内容 -->
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>服务连接配置</span>
              <el-button type="primary" @click="openServicesDialog">
                <el-icon><Edit /></el-icon> 配置
              </el-button>
            </div>
          </template>
          
          <el-row :gutter="20">
            <el-col :xs="24" :md="12" :lg="8" v-for="service in servicesList" :key="service.key">
              <div class="service-card" :class="{ configured: service.configured }">
                <div class="service-header">
                  <span class="service-name">{{ service.name }}</span>
                  <el-tag :type="service.configured ? 'success' : 'danger'" size="small">
                    {{ service.configured ? '已配置' : '未配置' }}
                  </el-tag>
                </div>
                <div class="service-url" v-if="service.url">{{ service.url }}</div>
                <div class="service-detail" v-if="service.detail">{{ service.detail }}</div>
                <div class="service-actions">
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="quickTestService(service.key)"
                    :loading="testingServices[service.key]"
                    :disabled="!service.configured"
                  >
                    <el-icon><Connection /></el-icon> 测试
                  </el-button>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>业务配置</span>
              <el-button type="primary" @click="openBusinessDialog">
                <el-icon><Edit /></el-icon> 编辑
              </el-button>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="Workflow 1 间隔">{{ config?.workflow1_interval_minutes }} 分钟</el-descriptions-item>
            <el-descriptions-item label="Workflow 2 间隔">{{ config?.workflow2_interval_minutes }} 分钟</el-descriptions-item>
            <el-descriptions-item label="Workflow 3 间隔">{{ config?.workflow3_interval_minutes }} 分钟</el-descriptions-item>
            <el-descriptions-item label="分享率阈值">{{ config?.javsp_submit_share_ratio }} ({{ (config?.javsp_submit_share_ratio || 0) * 100 }}%)</el-descriptions-item>
            <el-descriptions-item label="创建时间阈值">{{ config?.javsp_submit_hours }} 小时</el-descriptions-item>
            <el-descriptions-item label="最大保留完成数">{{ config?.max_completed_downloads }}</el-descriptions-item>
            <el-descriptions-item label="下载超时时间">{{ config?.download_timeout_hours }} 小时</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>Web UI 配置</span>
              <el-button type="primary" @click="openWebUIDialog">
                <el-icon><Edit /></el-icon> 编辑
              </el-button>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="登录密码">{{ config?.web_password ? '已设置' : '未设置' }}</el-descriptions-item>
            <el-descriptions-item label="JWT 密钥">{{ config?.web_secret_key ? '已设置' : '未设置' }}</el-descriptions-item>
          </el-descriptions>
          
          <div style="margin-top: 20px;">
            <el-button @click="backupDialogVisible = true">
              <el-icon><DocumentCopy /></el-icon> 备份管理
            </el-button>
            <el-button @click="exportConfig">
              <el-icon><Download /></el-icon> 导出配置
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Plus, Refresh, DocumentCopy, Download, Connection, InfoFilled, View, Hide, Check } from '@element-plus/icons-vue'
import { configApi, type ConfigResponse, type ConfigBackupInfo } from '@/api/config'
import { servicesApi, type ServicesStatusResponse } from '@/api/services'

const config = ref<ConfigResponse | null>(null)
const servicesStatus = ref<ServicesStatusResponse | null>(null)

// 对话框控制
const servicesDialogVisible = ref(false)
const businessDialogVisible = ref(false)
const webuiDialogVisible = ref(false)
const backupDialogVisible = ref(false)
const activeServiceTab = ref('freshrss')
const saving = ref(false)

// 编辑表单（完整）
const editForm = reactive({
  // Web UI
  web_password: '',
  web_secret_key: '',
  // FreshRSS
  freshrss_url: '',
  freshrss_username: '',
  freshrss_password: '',
  // RSSHub
  rsshub_base_url: '',
  // BitComet
  bitcomet_url: '',
  bitcomet_username: '',
  bitcomet_password: '',
  bitcomet_client_id: '',
  bitcomet_authentication: '',
  // JavSP
  javsp_url: '',
  javsp_username: '',
  javsp_password: '',
  // Jellyfin
  jellyfin_url: '',
  jellyfin_api_key: '',
  jellyfin_library_name: 'video',
  // 业务配置
  workflow1_interval_minutes: 10,
  workflow2_interval_minutes: 30,
  workflow3_interval_minutes: 60,
  javsp_submit_share_ratio: 2.0,
  javsp_submit_hours: 6.0,
  max_completed_downloads: 50,
  max_retry_count: 3,
  retry_delay_seconds: 60,
  download_timeout_hours: 48,
  bitcomet_download_path: '/home/sandbox/Downloads',
  javsp_input_path: '/video/downloaded',
  javsp_output_path: '/video',
})

// 测试服务状态
const testingServices = reactive({
  freshrss: false,
  rsshub: false,
  bitcomet: false,
  javsp: false,
  jellyfin: false,
})

// 密码可见性控制
const passwordVisible = reactive({
  freshrss: false,
  bitcomet: false,
  bitcomet_auth: false,
  javsp: false,
  jellyfin: false,
  webui: false,
  webui_key: false,
})

// 密码配置状态（从 API 获取）
const passwordConfigured = computed(() => ({
  freshrss: config.value?.freshrss_password_configured || false,
  bitcomet: config.value?.bitcomet_password_configured || false,
  bitcomet_auth: config.value?.bitcomet_authentication_configured || false,
  javsp: config.value?.javsp_password_configured || false,
  jellyfin: config.value?.jellyfin_api_key_configured || false,
}))

// 服务列表（用于展示）
const servicesList = computed(() => [
  {
    key: 'freshrss',
    name: 'FreshRSS',
    configured: servicesStatus.value?.freshrss.configured || false,
    url: servicesStatus.value?.freshrss.url,
    detail: servicesStatus.value?.freshrss.username,
  },
  {
    key: 'rsshub',
    name: 'RSSHub',
    configured: servicesStatus.value?.rsshub.configured || false,
    url: servicesStatus.value?.rsshub.url,
  },
  {
    key: 'bitcomet',
    name: 'BitComet',
    configured: servicesStatus.value?.bitcomet.configured || false,
    url: servicesStatus.value?.bitcomet.url,
    detail: servicesStatus.value?.bitcomet.has_auth ? '已设置认证' : '未设置认证',
  },
  {
    key: 'javsp',
    name: 'JavSP-Web',
    configured: servicesStatus.value?.javsp.configured || false,
    url: servicesStatus.value?.javsp.url,
  },
  {
    key: 'jellyfin',
    name: 'Jellyfin',
    configured: servicesStatus.value?.jellyfin.configured || false,
    url: servicesStatus.value?.jellyfin.url,
    detail: servicesStatus.value?.jellyfin.has_api_key ? '已设置 API Key' : '未设置 API Key',
  },
])

// 备份管理
const backups = ref<ConfigBackupInfo[]>([])
const loadingBackups = ref(false)
const creatingBackup = ref(false)
const restoring = ref<string | null>(null)
const deleting = ref<string | null>(null)

const fetchConfig = async () => {
  try {
    config.value = await configApi.getConfig()
  } catch (error) {
    console.error('获取配置失败', error)
    ElMessage.error('获取配置失败')
  }
}

const fetchServicesStatus = async () => {
  try {
    servicesStatus.value = await servicesApi.getServicesStatus()
  } catch (error) {
    console.error('获取服务状态失败', error)
  }
}

const initEditForm = () => {
  if (config.value) {
    // 对于已配置的密码字段，设置为空字符串（显示占位符）
    // 用户输入新值时会覆盖，留空则表示不修改
    Object.assign(editForm, {
      web_password: '',  // 密码始终不预填充
      web_secret_key: '',  // 密钥始终不预填充
      freshrss_url: config.value.freshrss_url || '',
      freshrss_username: config.value.freshrss_username || '',
      freshrss_password: '',  // 已配置时显示占位符，不预填充
      rsshub_base_url: config.value.rsshub_base_url || '',
      bitcomet_url: config.value.bitcomet_url || '',
      bitcomet_username: config.value.bitcomet_username || '',
      bitcomet_password: '',  // 已配置时显示占位符，不预填充
      bitcomet_client_id: config.value.bitcomet_client_id || '',
      bitcomet_authentication: '',  // 已配置时显示占位符，不预填充
      javsp_url: config.value.javsp_url || '',
      javsp_username: config.value.javsp_username || '',
      javsp_password: '',  // 已配置时显示占位符，不预填充
      jellyfin_url: config.value.jellyfin_url || '',
      jellyfin_api_key: '',  // 已配置时显示占位符，不预填充
      jellyfin_library_name: config.value.jellyfin_library_name || 'video',
      workflow1_interval_minutes: config.value.workflow1_interval_minutes,
      workflow2_interval_minutes: config.value.workflow2_interval_minutes,
      workflow3_interval_minutes: config.value.workflow3_interval_minutes,
      javsp_submit_share_ratio: config.value.javsp_submit_share_ratio,
      javsp_submit_hours: config.value.javsp_submit_hours,
      max_completed_downloads: config.value.max_completed_downloads,
      max_retry_count: config.value.max_retry_count,
      retry_delay_seconds: config.value.retry_delay_seconds,
      download_timeout_hours: config.value.download_timeout_hours,
      bitcomet_download_path: config.value.bitcomet_download_path,
      javsp_input_path: config.value.javsp_input_path,
      javsp_output_path: config.value.javsp_output_path,
    })
  }
}

const openServicesDialog = () => {
  initEditForm()
  servicesDialogVisible.value = true
}

const openBusinessDialog = () => {
  initEditForm()
  businessDialogVisible.value = true
}

const openWebUIDialog = () => {
  initEditForm()
  webuiDialogVisible.value = true
}

// 测试服务连接
const testService = async (service: string) => {
  testingServices[service as keyof typeof testingServices] = true
  
  try {
    let result
    
    switch (service) {
      case 'freshrss':
        result = await servicesApi.testFreshRSS({
          url: editForm.freshrss_url,
          username: editForm.freshrss_username,
          password: editForm.freshrss_password,
        })
        break
      case 'rsshub':
        result = await servicesApi.testRSSHub({
          url: editForm.rsshub_base_url,
        })
        break
      case 'bitcomet':
        result = await servicesApi.testBitComet({
          url: editForm.bitcomet_url,
          username: editForm.bitcomet_username,
          password: editForm.bitcomet_password,
          client_id: editForm.bitcomet_client_id,
          authentication: editForm.bitcomet_authentication,
        })
        break
      case 'javsp':
        result = await servicesApi.testJavSP({
          url: editForm.javsp_url,
          username: editForm.javsp_username,
          password: editForm.javsp_password,
        })
        break
      case 'jellyfin':
        result = await servicesApi.testJellyfin({
          url: editForm.jellyfin_url,
          api_key: editForm.jellyfin_api_key,
        })
        break
      default:
        return
    }
    
    if (result.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    console.error('测试失败', error)
    ElMessage.error('测试失败')
  } finally {
    testingServices[service as keyof typeof testingServices] = false
  }
}

// 快捷测试（从卡片按钮）
const quickTestService = async (service: string) => {
  if (!config.value) return
  
  testingServices[service as keyof typeof testingServices] = true
  
  try {
    let result
    
    switch (service) {
      case 'freshrss':
        result = await servicesApi.testFreshRSS({
          url: config.value.freshrss_url,
          username: config.value.freshrss_username,
          password: config.value.freshrss_password || '',
        })
        break
      case 'rsshub':
        result = await servicesApi.testRSSHub({
          url: config.value.rsshub_base_url,
        })
        break
      case 'bitcomet':
        result = await servicesApi.testBitComet({
          url: config.value.bitcomet_url,
          username: config.value.bitcomet_username,
          password: config.value.bitcomet_password || '',
          client_id: config.value.bitcomet_client_id || '',
          authentication: config.value.bitcomet_authentication || '',
        })
        break
      case 'javsp':
        result = await servicesApi.testJavSP({
          url: config.value.javsp_url,
          username: config.value.javsp_username,
          password: config.value.javsp_password || '',
        })
        break
      case 'jellyfin':
        result = await servicesApi.testJellyfin({
          url: config.value.jellyfin_url,
          api_key: config.value.jellyfin_api_key || '',
        })
        break
      default:
        return
    }
    
    if (result.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    console.error('测试失败', error)
    ElMessage.error('测试失败')
  } finally {
    testingServices[service as keyof typeof testingServices] = false
  }
}

// 保存单个服务配置
const saveSingleServiceConfig = async (service: string) => {
  saving.value = true
  try {
    const updates: Record<string, any> = {}
    
    switch (service) {
      case 'freshrss':
        updates.freshrss_url = editForm.freshrss_url
        updates.freshrss_username = editForm.freshrss_username
        // 只有当密码不为空时才更新（用户输入了新密码）
        if (editForm.freshrss_password) {
          updates.freshrss_password = editForm.freshrss_password
        }
        break
      case 'rsshub':
        updates.rsshub_base_url = editForm.rsshub_base_url
        break
      case 'bitcomet':
        updates.bitcomet_url = editForm.bitcomet_url
        updates.bitcomet_username = editForm.bitcomet_username
        updates.bitcomet_client_id = editForm.bitcomet_client_id
        // 只有当密码不为空时才更新
        if (editForm.bitcomet_password) {
          updates.bitcomet_password = editForm.bitcomet_password
        }
        if (editForm.bitcomet_authentication) {
          updates.bitcomet_authentication = editForm.bitcomet_authentication
        }
        break
      case 'javsp':
        updates.javsp_url = editForm.javsp_url
        updates.javsp_username = editForm.javsp_username
        // 只有当密码不为空时才更新
        if (editForm.javsp_password) {
          updates.javsp_password = editForm.javsp_password
        }
        break
      case 'jellyfin':
        updates.jellyfin_url = editForm.jellyfin_url
        updates.jellyfin_library_name = editForm.jellyfin_library_name
        // 只有当 API Key 不为空时才更新
        if (editForm.jellyfin_api_key) {
          updates.jellyfin_api_key = editForm.jellyfin_api_key
        }
        break
      default:
        return
    }
    
    const result = await configApi.updateConfig({ config: updates })
    if (result.success) {
      ElMessage.success(`${service} 配置保存成功`)
      // 清空已保存的密码字段
      if (service === 'freshrss') editForm.freshrss_password = ''
      if (service === 'bitcomet') {
        editForm.bitcomet_password = ''
        editForm.bitcomet_authentication = ''
      }
      if (service === 'javsp') editForm.javsp_password = ''
      if (service === 'jellyfin') editForm.jellyfin_api_key = ''
      
      fetchConfig()
      fetchServicesStatus()
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    console.error('保存失败', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 保存所有服务配置
const saveAllServicesConfig = async () => {
  saving.value = true
  try {
    const updates: Record<string, any> = {
      // FreshRSS
      freshrss_url: editForm.freshrss_url,
      freshrss_username: editForm.freshrss_username,
      // RSSHub
      rsshub_base_url: editForm.rsshub_base_url,
      // BitComet
      bitcomet_url: editForm.bitcomet_url,
      bitcomet_username: editForm.bitcomet_username,
      bitcomet_client_id: editForm.bitcomet_client_id,
      // JavSP
      javsp_url: editForm.javsp_url,
      javsp_username: editForm.javsp_username,
      // Jellyfin
      jellyfin_url: editForm.jellyfin_url,
      jellyfin_library_name: editForm.jellyfin_library_name,
    }
    
    // 只有当密码不为空时才更新
    if (editForm.freshrss_password) {
      updates.freshrss_password = editForm.freshrss_password
    }
    if (editForm.bitcomet_password) {
      updates.bitcomet_password = editForm.bitcomet_password
    }
    if (editForm.bitcomet_authentication) {
      updates.bitcomet_authentication = editForm.bitcomet_authentication
    }
    if (editForm.javsp_password) {
      updates.javsp_password = editForm.javsp_password
    }
    if (editForm.jellyfin_api_key) {
      updates.jellyfin_api_key = editForm.jellyfin_api_key
    }
    
    const result = await configApi.updateConfig({ config: updates })
    if (result.success) {
      ElMessage.success('所有服务配置保存成功')
      servicesDialogVisible.value = false
      fetchConfig()
      fetchServicesStatus()
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    console.error('保存失败', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const saveBusinessConfig = async () => {
  saving.value = true
  try {
    const result = await configApi.updateConfig({
      config: {
        workflow1_interval_minutes: editForm.workflow1_interval_minutes,
        workflow2_interval_minutes: editForm.workflow2_interval_minutes,
        workflow3_interval_minutes: editForm.workflow3_interval_minutes,
        javsp_submit_share_ratio: editForm.javsp_submit_share_ratio,
        javsp_submit_hours: editForm.javsp_submit_hours,
        max_completed_downloads: editForm.max_completed_downloads,
        max_retry_count: editForm.max_retry_count,
        retry_delay_seconds: editForm.retry_delay_seconds,
        download_timeout_hours: editForm.download_timeout_hours,
        bitcomet_download_path: editForm.bitcomet_download_path,
        javsp_input_path: editForm.javsp_input_path,
        javsp_output_path: editForm.javsp_output_path,
      }
    })
    if (result.success) {
      ElMessage.success('业务配置保存成功')
      businessDialogVisible.value = false
      fetchConfig()
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    console.error('保存失败', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const saveWebUIConfig = async () => {
  saving.value = true
  try {
    const updates: Record<string, any> = {}
    
    // 只有当密码不为空时才更新
    if (editForm.web_password) {
      updates.web_password = editForm.web_password
    }
    if (editForm.web_secret_key) {
      updates.web_secret_key = editForm.web_secret_key
    }
    
    // 如果没有要更新的字段，直接关闭
    if (Object.keys(updates).length === 0) {
      ElMessage.info('没有修改的配置')
      webuiDialogVisible.value = false
      return
    }
    
    const result = await configApi.updateConfig({ config: updates })
    if (result.success) {
      ElMessage.success('Web UI 配置保存成功')
      webuiDialogVisible.value = false
      // 清空密码字段
      editForm.web_password = ''
      editForm.web_secret_key = ''
      fetchConfig()
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    console.error('保存失败', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 备份管理
const fetchBackups = async () => {
  loadingBackups.value = true
  try {
    backups.value = await configApi.listBackups()
  } catch (error) {
    console.error('获取备份列表失败', error)
    ElMessage.error('获取备份列表失败')
  } finally {
    loadingBackups.value = false
  }
}

const createBackup = async () => {
  creatingBackup.value = true
  try {
    const result = await configApi.backupConfig()
    if (result.success) {
      ElMessage.success(result.message)
      fetchBackups()
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    console.error('创建备份失败', error)
    ElMessage.error('创建备份失败')
  } finally {
    creatingBackup.value = false
  }
}

const restoreBackup = async (backupName: string) => {
  try {
    await ElMessageBox.confirm(
      `确定要从 ${backupName} 恢复配置吗？当前配置将自动备份。`,
      '确认恢复',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    
    restoring.value = backupName
    const result = await configApi.restoreConfig(backupName)
    if (result.success) {
      ElMessage.success(result.message)
      fetchConfig()
      fetchServicesStatus()
      backupDialogVisible.value = false
    } else {
      ElMessage.error(result.message)
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('恢复备份失败', error)
      ElMessage.error('恢复备份失败')
    }
  } finally {
    restoring.value = null
  }
}

const deleteBackup = async (backupName: string) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除备份 ${backupName} 吗？此操作不可恢复。`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'danger' }
    )
    
    deleting.value = backupName
    const result = await configApi.deleteBackup(backupName)
    if (result.success) {
      ElMessage.success(result.message)
      fetchBackups()
    } else {
      ElMessage.error(result.message)
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除备份失败', error)
      ElMessage.error('删除备份失败')
    }
  } finally {
    deleting.value = null
  }
}

const exportConfig = async () => {
  try {
    const data = await configApi.exportConfig()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `avdm-config-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('配置导出成功')
  } catch (error) {
    console.error('导出配置失败', error)
    ElMessage.error('导出配置失败')
  }
}

// 工具函数
const formatDate = (dateStr: string) => new Date(dateStr).toLocaleString('zh-CN')
const formatSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

onMounted(() => {
  fetchConfig()
  fetchServicesStatus()
  fetchBackups()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@media (max-width: 768px) {
  .settings-page .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}

.service-card {
  border: 1px solid var(--dm-border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  background: var(--dm-bg-hover);
  transition: all 0.3s;
}

.service-card.configured {
  background: var(--dm-sidebar-active-bg);
  border-color: var(--dm-sidebar-active-text);
}

.service-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.service-name {
  font-weight: bold;
  font-size: 16px;
}

.service-url {
  color: var(--dm-text-secondary);
  font-size: 12px;
  word-break: break-all;
  margin-bottom: 4px;
}

.service-detail {
  color: var(--dm-text-muted);
  font-size: 12px;
  margin-bottom: 12px;
}

.service-actions {
  display: flex;
  justify-content: flex-end;
}

.form-hint {
  color: var(--dm-text-muted);
  font-size: 12px;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.backup-actions {
  display: flex;
  gap: 12px;
}

:deep(.el-divider__text) {
  font-size: 12px;
  color: var(--dm-text-muted);
}

:deep(.services-dialog .el-dialog__body) {
  padding-top: 0;
}

.password-eye {
  cursor: pointer;
  color: var(--dm-text-muted);
  transition: color 0.3s;
}

.password-eye:hover {
  color: var(--dm-sidebar-active-text);
}

.settings-page .el-card {
  border-radius: 12px;
}

.settings-page .service-name {
  color: var(--dm-text-primary);
  font-weight: 600;
  transition: color 0.3s ease;
}
</style>
