<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
} from 'vue'

import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

import {
  Right,
  Position,
  Calendar,
  WarningFilled,
  Warning,
  RemoveFilled,
  InfoFilled,
  Lock,
} from '@element-plus/icons-vue'

import {
  getAssets,
  getFindings,
  getScans,
} from '../../api'

const router = useRouter()

const target = ref('')
const loading = ref(false)

const assets = ref([])
const scans = ref([])
const findings = ref([])

const findingChartRef = ref(null)
const trendChartRef = ref(null)

let findingChart = null
let trendChart = null

const severity = [
  {
    label: '严重风险',
    english: 'Critical',
    key: 'critical',
    color: '#df5965',
    tint: '#fff0f2',
    icon: WarningFilled,
  },
  {
    label: '高危风险',
    english: 'High',
    key: 'high',
    color: '#e68b3e',
    tint: '#fff5eb',
    icon: Warning,
  },
  {
    label: '中危风险',
    english: 'Medium',
    key: 'medium',
    color: '#d4aa26',
    tint: '#fff9e7',
    icon: RemoveFilled,
  },
  {
    label: '低危风险',
    english: 'Low',
    key: 'low',
    color: '#299dbc',
    tint: '#ebf8fc',
    icon: InfoFilled,
  },
]

const findingLegend = [
  ...severity,
  {
    label: '信息',
    english: 'Info',
    key: 'info',
    color: '#91a4ba',
  },
]

function normalizeList(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.items)) {
    return data.items
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

const severityCounts = computed(() => {
  const counts = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  }

  for (const finding of findings.value) {
    const level = String(
      finding.risk_level ||
        finding.severity ||
        '',
    ).toLowerCase()

    if (level in counts) {
      counts[level] += 1
    }
  }

  return counts
})

const todayScanCount = computed(() => {
  const today = new Date().toDateString()

  return scans.value.filter((scan) => {
    const rawDate =
      scan.created_at ||
      scan.started_at

    if (!rawDate) {
      return false
    }

    const date = new Date(rawDate)

    if (Number.isNaN(date.getTime())) {
      return false
    }

    return date.toDateString() === today
  }).length
})

const recentScans = computed(() =>
  [...scans.value]
    .sort((a, b) => {
      const left = new Date(
        a.created_at ||
          a.started_at ||
          0,
      ).getTime()

      const right = new Date(
        b.created_at ||
          b.started_at ||
          0,
      ).getTime()

      return right - left
    })
    .slice(0, 5),
)

function buildLast7DaysTrend() {
  const days = []

  for (let offset = 6; offset >= 0; offset -= 1) {
    const date = new Date()

    date.setHours(0, 0, 0, 0)
    date.setDate(date.getDate() - offset)

    days.push({
      timestamp: date.getTime(),
      label: `${date.getMonth() + 1}/${date.getDate()}`,
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
    })
  }

  for (const finding of findings.value) {
    if (!finding.created_at) {
      continue
    }

    const createdAt = new Date(finding.created_at)

    if (Number.isNaN(createdAt.getTime())) {
      continue
    }

    createdAt.setHours(0, 0, 0, 0)

    const day = days.find(
      (item) =>
        item.timestamp === createdAt.getTime(),
    )

    if (!day) {
      continue
    }

    const level = String(
      finding.risk_level ||
        finding.severity ||
        '',
    ).toLowerCase()

    if (
      level === 'critical' ||
      level === 'high' ||
      level === 'medium' ||
      level === 'low'
    ) {
      day[level] += 1
    }
  }

  return days
}

function renderTrendChart() {
  if (!trendChartRef.value) {
    return
  }

  if (!trendChart) {
    trendChart = echarts.init(
      trendChartRef.value,
    )
  }

  const trend = buildLast7DaysTrend()

  trendChart.setOption({
    animationDuration: 500,

    tooltip: {
      trigger: 'axis',
    },

    grid: {
      top: 24,
      left: 38,
      right: 18,
      bottom: 32,
    },

    xAxis: {
      type: 'category',
      boundaryGap: false,

      data: trend.map(
        (item) => item.label,
      ),

      axisLine: {
        lineStyle: {
          color: '#e6eaf0',
        },
      },

      axisTick: {
        show: false,
      },

      axisLabel: {
        color: '#8a95a8',
        fontSize: 11,
      },
    },

    yAxis: {
      type: 'value',
      min: 0,
      minInterval: 1,

      axisLine: {
        show: false,
      },

      axisTick: {
        show: false,
      },

      axisLabel: {
        color: '#8a95a8',
        fontSize: 11,
      },

      splitLine: {
        lineStyle: {
          color: '#edf0f4',
        },
      },
    },

    series: [
      {
        name: 'Critical',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,

        data: trend.map(
          (item) => item.critical,
        ),

        lineStyle: {
          width: 2,
          color: '#df5965',
        },

        itemStyle: {
          color: '#df5965',
        },
      },

      {
        name: 'High',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,

        data: trend.map(
          (item) => item.high,
        ),

        lineStyle: {
          width: 2,
          color: '#e68b3e',
        },

        itemStyle: {
          color: '#e68b3e',
        },
      },

      {
        name: 'Medium',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,

        data: trend.map(
          (item) => item.medium,
        ),

        lineStyle: {
          width: 2,
          color: '#d4aa26',
        },

        itemStyle: {
          color: '#d4aa26',
        },
      },

      {
        name: 'Low',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,

        data: trend.map(
          (item) => item.low,
        ),

        lineStyle: {
          width: 2,
          color: '#299dbc',
        },

        itemStyle: {
          color: '#299dbc',
        },
      },
    ],
  })
}

function renderFindingChart() {
  if (!findingChartRef.value) {
    return
  }

  if (!findingChart) {
    findingChart = echarts.init(
      findingChartRef.value,
    )
  }

  findingChart.setOption({
    animationDuration: 500,

    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },

    legend: {
      show: false,
    },

    series: [
      {
        name: 'Finding Severity',
        type: 'pie',

        radius: [
          '64%',
          '82%',
        ],

        center: [
          '50%',
          '50%',
        ],

        avoidLabelOverlap: true,

        label: {
          show: false,
        },

        labelLine: {
          show: false,
        },

        data: [
          {
            value:
              severityCounts.value.critical,
            name: 'Critical',

            itemStyle: {
              color: '#df5965',
            },
          },

          {
            value:
              severityCounts.value.high,
            name: 'High',

            itemStyle: {
              color: '#e68b3e',
            },
          },

          {
            value:
              severityCounts.value.medium,
            name: 'Medium',

            itemStyle: {
              color: '#d4aa26',
            },
          },

          {
            value:
              severityCounts.value.low,
            name: 'Low',

            itemStyle: {
              color: '#299dbc',
            },
          },

          {
            value:
              severityCounts.value.info,
            name: 'Info',

            itemStyle: {
              color: '#91a4ba',
            },
          },
        ],
      },
    ],
  })
}

function resizeCharts() {
  findingChart?.resize()
  trendChart?.resize()
}

async function loadDashboard() {
  loading.value = true

  try {
    const [
      assetsData,
      scansData,
      findingsData,
    ] = await Promise.all([
      getAssets({
        silent: true,
      }),

      getScans({
        silent: true,
      }),

      getFindings({
        silent: true,
      }),
    ])

    assets.value =
      normalizeList(assetsData)

    scans.value =
      normalizeList(scansData)

    findings.value =
      normalizeList(findingsData)
  } catch (error) {
    console.error(
      'Failed to load dashboard:',
      error,
    )

    ElMessage.warning(
      'Dashboard 数据加载失败，请确认后端接口是否正常',
    )
  } finally {
    loading.value = false
  }
}

function prepareScan() {
  const value = target.value.trim()

  if (!value) {
    ElMessage.warning(
      '请输入目标 URL、域名或 IP 地址',
    )

    return
  }

  router.push({
    name: 'scans',

    query: {
      target: value,
    },
  })
}

onMounted(async () => {
  await loadDashboard()
  await nextTick()

  renderFindingChart()
  renderTrendChart()

  window.addEventListener(
    'resize',
    resizeCharts,
  )
})

onBeforeUnmount(() => {
  window.removeEventListener(
    'resize',
    resizeCharts,
  )

  findingChart?.dispose()
  findingChart = null

  trendChart?.dispose()
  trendChart = null
})
</script>

<template>
  <div class="dashboard">
    <div class="page-heading">
      <div>
        <div class="eyebrow">
          SECURITY OVERVIEW
        </div>

        <h2>
          Security Dashboard
        </h2>

        <p>
          SentinelAgent AI-Powered Security Operations Platform
        </p>
      </div>

      <el-tag
        :type="loading ? 'info' : 'success'"
        effect="plain"
      >
        {{
          loading
            ? '正在读取安全数据'
            : `${assets.length} 资产 · ${scans.length} 扫描 · ${findings.length} Findings`
        }}
      </el-tag>
    </div>

    <div class="quick-row">
      <section class="quick-scan">
        <h3>
          <el-icon>
            <Lock />
          </el-icon>

          快速安全扫描
        </h3>

        <p>
          输入目标地址，前往扫描任务配置
        </p>

        <form
          class="quick-form"
          @submit.prevent="prepareScan"
        >
          <el-input
            v-model="target"
            aria-label="扫描目标"
            placeholder="https://example.com 或 192.168.1.1"
            clearable
          />

          <el-button native-type="submit">
            <el-icon>
              <Position />
            </el-icon>

            配置扫描
          </el-button>
        </form>
      </section>

      <section class="today-card panel">
        <div>
          <span class="muted">
            今日扫描数
          </span>

          <strong>
            {{
              loading
                ? '—'
                : todayScanCount
            }}
          </strong>

          <small>
            {{
              loading
                ? '正在读取扫描数据'
                : `累计扫描任务 ${scans.length}`
            }}
          </small>
        </div>

        <span class="calendar-icon">
          <el-icon>
            <Calendar />
          </el-icon>
        </span>
      </section>
    </div>

    <div class="severity-grid">
      <section
        v-for="item in severity"
        :key="item.english"
        class="severity-card panel"
        :style="{
          '--severity': item.color,
          '--severity-tint': item.tint,
        }"
      >
        <div>
          <span>
            {{ item.label }}

            <small>
              {{ item.english }}
            </small>
          </span>

          <strong>
            {{
              loading
                ? '—'
                : severityCounts[item.key]
            }}
          </strong>
        </div>

        <span class="severity-icon">
          <el-icon>
            <component
              :is="item.icon"
            />
          </el-icon>
        </span>
      </section>
    </div>

    <div class="chart-grid">
      <section class="panel chart-panel">
        <div class="panel-heading">
          <h3>
            风险趋势

            <small>
              Risk trend
            </small>
          </h3>

          <span class="muted">
            最近 7 天
          </span>
        </div>

        <div
          ref="trendChartRef"
          class="trend-chart"
        ></div>

        <div class="chart-legend">
          <span
            v-for="item in severity"
            :key="item.english"
          >
            <i
              :style="{
                background: item.color,
              }"
            ></i>

            {{ item.english }}
          </span>
        </div>
      </section>

      <section class="panel chart-panel">
        <div class="panel-heading">
          <h3>
            Finding 分布

            <small>
              Severity distribution
            </small>
          </h3>

          <span class="muted">
            全部发现
          </span>
        </div>

        <div class="distribution">
          <div class="finding-chart-wrap">
            <div
              ref="findingChartRef"
              class="finding-chart"
            ></div>

            <div class="finding-chart-center">
              <strong>
                {{
                  loading
                    ? '—'
                    : findings.length
                }}
              </strong>

              <span>
                Findings
              </span>
            </div>
          </div>

          <div class="distribution-summary">
            <h4>
              安全发现总览
            </h4>

            <p>
              Critical
              {{ severityCounts.critical }}
              · High
              {{ severityCounts.high }}
              · Medium
              {{ severityCounts.medium }}
              · Low
              {{ severityCounts.low }}
            </p>

            <small class="muted">
              Info
              {{ severityCounts.info }}
            </small>
          </div>
        </div>

        <div class="chart-legend">
          <span
            v-for="item in findingLegend"
            :key="item.english"
          >
            <i
              :style="{
                background: item.color,
              }"
            ></i>

            {{ item.english }}
          </span>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel-heading">
        <h3>
          最近扫描任务

          <small>
            Recent scans
          </small>
        </h3>

        <router-link
          class="text-link"
          to="/scans"
        >
          查看全部

          <el-icon>
            <Right />
          </el-icon>
        </router-link>
      </div>

      <el-table
        :data="recentScans"
        v-loading="loading"
        empty-text="暂无扫描任务"
      >
        <el-table-column
          prop="id"
          label="任务 ID"
          width="100"
        />

        <el-table-column
          label="资产"
          width="120"
        >
          <template #default="{ row }">
            #{{ row.asset_id ?? '—' }}
          </template>
        </el-table-column>

        <el-table-column
          prop="status"
          label="状态"
          width="130"
        />

        <el-table-column
          prop="started_at"
          label="开始时间"
        />

        <el-table-column
          prop="finished_at"
          label="结束时间"
        />
      </el-table>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <h3>
          最近 Agent Investigation

          <small>
            AI 调查
          </small>
        </h3>

        <router-link
          class="text-link"
          to="/investigations"
        >
          进入调查中心

          <el-icon>
            <Right />
          </el-icon>
        </router-link>
      </div>

      <el-table
        :data="[]"
        empty-text="暂无 AI 调查 · Day31 接入 LangGraph 调查工作流"
      >
        <el-table-column
          label="Investigation Run"
        />

        <el-table-column
          label="关联 Finding"
        />

        <el-table-column
          label="当前阶段"
        />

        <el-table-column
          label="Final Verdict"
        />

        <el-table-column
          label="更新时间"
        />
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.trend-chart {
  width: 100%;
  height: 250px;
}

.finding-chart-wrap {
  position: relative;
  width: 180px;
  height: 180px;
  flex-shrink: 0;
}

.finding-chart {
  width: 100%;
  height: 100%;
}

.finding-chart-center {
  position: absolute;
  top: 50%;
  left: 50%;

  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  transform: translate(-50%, -50%);
  pointer-events: none;
}

.finding-chart-center strong {
  color: #334155;
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
}

.finding-chart-center span {
  margin-top: 6px;

  color: #94a3b8;
  font-size: 11px;
}

.distribution-summary {
  min-width: 0;
}

.distribution-summary h4 {
  margin-bottom: 10px;
}

.distribution-summary p {
  line-height: 1.8;
}

@media (max-width: 1200px) {
  .trend-chart {
    height: 220px;
  }

  .finding-chart-wrap {
    width: 160px;
    height: 160px;
  }
}
</style>