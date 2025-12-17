// 国际化配置和翻译文件

export type Locale = 'en' | 'zh'

export const locales: Locale[] = ['en', 'zh']

export const defaultLocale: Locale = 'zh'

// 翻译键类型定义
export interface Translations {
  // Common
  common: {
    loading: string
    error: string
    success: string
    save: string
    cancel: string
    delete: string
    edit: string
    add: string
    search: string
    filter: string
    refresh: string
    export: string
    confirm: string
    close: string
    back: string
    next: string
    previous: string
    apply: string
    reset: string
    select: string
    all: string
    none: string
    total: string
    average: string
    maximum: string
    minimum: string
    to: string
  }
  
  // Navigation
  nav: {
    dashboard: string
    resources: string
    costAnalysis: string
    budget: string
    customDashboards: string
    discountAnalysis: string
    virtualTags: string
    security: string
    optimization: string
    reports: string
    settings: string
  }
  
  // Dashboard
  dashboard: {
    title: string
    account: string
    scanNow: string
    scanning: string
    totalCost: string
    monthlyEstimate: string
    costTrend: string
    comparedToLastMonth: string
    idleResources: string
    suggestHandle: string
    totalResources: string
    alertCount: string
    needAttention: string
    tagCoverage: string
    resourceTagCompleteness: string
    savingsPotential: string
    monthlySavingsPotential: string
    costTrendChart: string
    idleResourcesTable: string
    selectAccount: string
    selectAccountDesc: string
    goToAccountManagement: string
  }
  
  // Cost
  cost: {
    title: string
    currentMonth: string
    lastMonth: string
    costBreakdown: string
    costTrend: string
    days: string
    all: string
    custom: string
    startDate: string
    endDate: string
  }
  
  // Resources
  resources: {
    title: string
    description: string
    resourceList: string
    nameId: string
    type: string
    status: string
    region: string
    spec: string
    monthlyCost: string
    createdTime: string
    vpc: string
    noResources: string
    searchPlaceholder: string
    totalResources: string
    page: string
    previousPage: string
    nextPage: string
  }
  
  // Settings
  settings: {
    title: string
    accounts: string
    rules: string
    saveSuccess: string
    saveFailed: string
  }
  
  // Date Range
  dateRange: {
    all: string
    last7Days: string
    last30Days: string
    last90Days: string
    custom: string
    startDate: string
    endDate: string
    apply: string
  }
  
  // Trend
  trend: {
    up: string
    down: string
    stable: string
    unknown: string
    insufficientData: string
  }
  
  // Discount Analysis
  discounts: {
    title: string
    description: string
    billingCycle: string
    current: string
    originalPrice: string
    discountedPrice: string
    savings: string
    savingsDiscount: string
    overallDiscount: string
    details: string
    product: string
    billingType: string
    subscription: string
    payAsYouGo: string
    free: string
    unpaid: string
    actualPaymentRate: string
    searchPlaceholder: string
    loadCache: string
    forceRefresh: string
    loadingCache: string
    forceRefreshing: string
    cancelRequest: string
    loadFailed: string
    timeoutMessage: string
    note: string
    all: string
    waited: string
  }
  
  // Advanced Discount Analysis
  discountAdvanced: {
    title: string
    description: string
    exportExcel: string
    refresh: string
    loading: string
    loadFailed: string
    tabs: {
      overview: string
      timeAnalysis: string
      productAnalysis: string
      regionAnalysis: string
      billingAnalysis: string
      advancedAnalysis: string
    }
    overview: {
      latestQuarterDiscount: string
      quarterTotalSavings: string
      optimizationOpportunities: string
      anomalyDetection: string
      quarterlyTrend: string
      top5ProductDiscount: string
      aiInsights: string
      generatingInsights: string
      months: string
      instances: string
      monthsUnit: string
      yearSavings: string
      fluctuation: string
      discountAmount: string
      discountRate: string
      avgDiscountRate: string
      momChange: string
    }
    timeAnalysis: {
      quarterComparison: string
      yearlyComparison: string
      discountAnomaly: string
      paidAmount: string
    }
    productAnalysis: {
      selectProducts: string
      productTrendComparison: string
      productRanking: string
      productName: string
      totalConsumption: string
      totalDiscount: string
      volatility: string
      trend: string
    }
    regionAnalysis: {
      regionRanking: string
      regionDetails: string
      region: string
      consumptionAmount: string
      instanceCount: string
      productCount: string
      percentage: string
    }
    billingAnalysis: {
      billingComparison: string
      discountRateComparison: string
      subscriptionAdvantage: string
      subscriptionHigher: string
      optimizationSuggestions: string
      instanceId: string
      runningMonths: string
      currentDiscount: string
      estimatedDiscount: string
      annualSavings: string
      consumptionAmount: string
      consumptionPercentage: string
    }
    advanced: {
      movingAverage: string
      cumulativeDiscount: string
      cumulativeTotal: string
      monthlyAverage: string
      phase2Insights: string
      trendSmoothing: string
      cumulativeSavings: string
      dataInsights: string
      originalData: string
      monthMovingAverage: string
      cumulativeDiscountAmount: string
      monthlyDiscount: string
      rising: string
      falling: string
    }
  }
  
  // Cost Analysis (extended)
  costAnalysis: {
    title: string
    description: string
    currentMonthCost: string
    lastMonthCost: string
    momGrowth: string
    yoyGrowth: string
    costBreakdown: string
    other: string
    viewAndAnalyze: string
  }
  
  // Accounts
  accounts: {
    title: string
    description: string
    addAccount: string
    configuredAccounts: string
    noAccounts: string
    noAccountsDesc: string
    region: string
    delete: string
    confirmDelete: string
    confirmDeleteMessage: string
    addCloudAccount: string
    addAccountDesc: string
    accountName: string
    accountNamePlaceholder: string
    provider: string
    aliyun: string
    tencent: string
    regionPlaceholder: string
    accessKeyId: string
    accessKeySecret: string
    secretNote: string
    hide: string
    show: string
    nameRequired: string
    keyIdRequired: string
    secretRequired: string
    saving: string
    saveAndSwitch: string
  }
  
  // Optimization
  optimization: {
    title: string
    description: string
    noSuggestions: string
    noSuggestionsDesc: string
    totalSavingsPotential: string
    monthlySavingsPotential: string
    suggestionCount: string
    suggestions: string
    highPriority: string
    needImmediateAttention: string
    mediumPriority: string
    suggestHandleSoon: string
    lowPriority: string
    all: string
    costOptimization: string
    securityOptimization: string
    resourceManagement: string
    relatedResources: string
    savingsPotential: string
    optimizationSuggestion: string
    unit: string
    perMonth: string
  }
  
  // Budget
  budget: {
    title: string
    description: string
    budgetSettings: string
    monthlyBudget: string
    annualBudget: string
    saveBudget: string
    saving: string
    budgetUsage: string
    currentMonthUsed: string
    usageRate: string
    selectAccountFirst: string
    saveSuccess: string
    saveFailed: string
    deleteConfirm: string
    deleteFailed: string
    createBudget: string
    searchPlaceholder: string
    noBudgets: string
    noBudgetsDesc: string
    noMatchBudgets: string
    tryOtherKeywords: string
    budgetAmount: string
    spent: string
    remaining: string
    usageProgress: string
    days: string
    predictedSpend: string
    predictedOverspend: string
    alertTriggered: string
    period: {
      monthly: string
      quarterly: string
      yearly: string
    }
    scope: {
      total: string
      tag: string
      service: string
    }
  }
  
  // Reports
  reports: {
    title: string
    description: string
    selectReportType: string
    selectFormat: string
    generateReport: string
    selected: string
    format: string
    reportType: string
    outputFormat: string
    generating: string
    generateAndDownload: string
    tip: string
    tipContent: string
    excelTip: string
    htmlTip: string
    pdfTip: string
    selectAccountFirst: string
    generateSuccess: string
    generateFailed: string
    types: {
      comprehensive: {
        name: string
        description: string
      }
      resource: {
        name: string
        description: string
      }
      cost: {
        name: string
        description: string
      }
      security: {
        name: string
        description: string
      }
    }
    formats: {
      excel: {
        name: string
        description: string
      }
      html: {
        name: string
        description: string
      }
      pdf: {
        name: string
        description: string
      }
    }
  }
  
  // Security
  security: {
    title: string
    description: string
    securityScore: string
    publicExposure: string
    highRiskResources: string
    diskEncryptionRate: string
    encrypted: string
    tagCoverage: string
    resourcesMissingTags: string
    securityImprovements: string
    detailedResults: string
    foundIssues: string
    issues: string
    coverage: string
    encryptionRate: string
    suggestion: string
    problemResources: string
    region: string
    points: string
    ip: string
  }
  
  // Alerts
  alerts: {
    title: string
    description: string
    createRule: string
    rules: string
    records: string
    alertRules: string
    manageRules: string
    noRules: string
    noRulesDesc: string
    enabled: string
    disabled: string
    type: string
    metric: string
    threshold: string
    check: string
    edit: string
    delete: string
    deleteConfirm: string
    deleteFailed: string
    updateFailed: string
    checkFailed: string
    triggered: string
    acknowledged: string
    resolved: string
    closed: string
    alertTriggered: string
    alertNotTriggered: string
    triggerTime: string
    alertRecords: string
    viewAndManageRecords: string
    noRecords: string
    noRecordsDesc: string
    rule: string
    metricValue: string
    confirm: string
    resolve: string
    close: string
    enable: string
    disable: string
    editRule: string
    createRule: string
    configureRule: string
    alertType: string
    costThreshold: string
  }
}

// 英文翻译
const en: Translations = {
  common: {
    loading: 'Loading...',
    error: 'Error',
    success: 'Success',
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    edit: 'Edit',
    add: 'Add',
    search: 'Search',
    filter: 'Filter',
    refresh: 'Refresh',
    export: 'Export',
    confirm: 'Confirm',
    close: 'Close',
    back: 'Back',
    next: 'Next',
    previous: 'Previous',
    apply: 'Apply',
    reset: 'Reset',
    select: 'Select',
    all: 'All',
    none: 'None',
    total: 'Total',
    average: 'Average',
    maximum: 'Maximum',
    minimum: 'Minimum',
    to: 'to',
  },
  nav: {
    dashboard: 'Dashboard',
    resources: 'Resources',
    costAnalysis: 'Cost Analysis',
    budget: 'Budget',
    customDashboards: 'Custom Dashboards',
    discountAnalysis: 'Discount Analysis',
    virtualTags: 'Virtual Tags',
    security: 'Security',
    optimization: 'Optimization',
    reports: 'Reports',
    settings: 'Settings',
  },
  dashboard: {
    title: 'Dashboard',
    account: 'Account',
    scanNow: 'Scan Now',
    scanning: 'Scanning...',
    totalCost: 'Total Estimated Cost',
    monthlyEstimate: 'Monthly Estimated Expense',
    costTrend: 'Cost Trend',
    comparedToLastMonth: 'Compared to Last Month',
    idleResources: 'Idle Resources',
    suggestHandle: 'Suggest Handle Soon',
    totalResources: 'Total Resources',
    alertCount: 'Alerts',
    needAttention: 'Need Attention',
    tagCoverage: 'Tag Coverage',
    resourceTagCompleteness: 'Resource Tag Completeness',
    savingsPotential: 'Savings Potential',
    monthlySavingsPotential: 'Monthly Savings Potential',
    costTrendChart: 'Cost Trend',
    idleResourcesTable: 'Idle Resources',
    selectAccount: 'Please Select Account',
    selectAccountDesc: 'Please select a cloud account from the left sidebar',
    goToAccountManagement: 'Go to Account Management',
  },
  cost: {
    title: 'Cost Analysis',
    currentMonth: 'Current Month',
    lastMonth: 'Last Month',
    costBreakdown: 'Cost Breakdown',
    costTrend: 'Cost Trend',
    days: 'Days',
    all: 'All',
    custom: 'Custom',
    startDate: 'Start Date',
    endDate: 'End Date',
  },
  resources: {
    title: 'Resource Management',
    description: 'View and manage all cloud resources',
    resourceList: 'Resource List',
    nameId: 'Name / ID',
    type: 'Type',
    status: 'Status',
    region: 'Region',
    spec: 'Spec',
    monthlyCost: 'Monthly Cost',
    createdTime: 'Created Time',
    vpc: 'VPC',
    noResources: 'No Resources Found',
    searchPlaceholder: 'Search resources...',
    totalResources: 'Total {total} resources, Page {page} / {totalPages}',
    page: 'Page',
    previousPage: 'Previous',
    nextPage: 'Next',
  },
  settings: {
    title: 'Settings',
    accounts: 'Accounts',
    rules: 'Rules',
    saveSuccess: 'Settings saved successfully!',
    saveFailed: 'Save failed',
  },
  dateRange: {
    all: 'All',
    last7Days: '7 Days',
    last30Days: '30 Days',
    last90Days: '90 Days',
    custom: 'Custom',
    startDate: 'Start Date',
    endDate: 'End Date',
    apply: 'Apply',
  },
  trend: {
    up: 'Up',
    down: 'Down',
    stable: 'Stable',
    unknown: 'Unknown',
    insufficientData: 'Insufficient Data',
  },
  discounts: {
    title: 'Discount Analysis',
    description: 'Discount summary by product + billing type (Subscription / PayAsYouGo)',
    billingCycle: 'Billing Cycle',
    current: 'Current',
    originalPrice: 'Original Price (Pre-tax)',
    discountedPrice: 'Discounted (Pre-tax)',
    savings: 'Savings',
    savingsDiscount: 'Savings / Discount',
    overallDiscount: 'Overall Discount',
    details: 'Details',
    product: 'Product',
    billingType: 'Billing Type',
    subscription: 'Subscription',
    payAsYouGo: 'PayAsYouGo',
    free: 'Free',
    unpaid: 'Unpaid',
    actualPaymentRate: 'Actual Payment Rate',
    searchPlaceholder: 'Search product/code...',
    loadCache: 'Load Cache',
    forceRefresh: 'Force Refresh',
    loadingCache: 'Loading: Reading cache first (faster)...',
    forceRefreshing: 'Force refreshing: Fetching Aliyun billing and discount data...',
    cancelRequest: 'Cancel Request',
    loadFailed: 'Load Failed',
    timeoutMessage: 'Request timeout (waited {seconds}s). You can try "Load Cache" first, or click "Force Refresh" later.',
    note: 'Note: PayAsYouGo may have unpaid amounts (PaymentAmount=0), please refer to "Unpaid" and "Discounted (Pre-tax)" for understanding.',
    all: 'All',
    waited: 'Waited {seconds}s',
  },
  discountAdvanced: {
    title: 'Advanced Discount Analysis',
    description: 'Multi-dimensional deep analysis • 8 major analysis dimensions • Custom time range',
    exportExcel: 'Export Excel',
    refresh: 'Refresh',
    loading: 'Loading advanced discount analysis...',
    loadFailed: 'Load Failed',
    tabs: {
      overview: 'Overview',
      timeAnalysis: 'Time Analysis',
      productAnalysis: 'Product Analysis',
      regionAnalysis: 'Region Analysis',
      billingAnalysis: 'Billing Analysis',
      advancedAnalysis: 'Advanced Analysis',
    },
    overview: {
      latestQuarterDiscount: 'Latest Quarterly Discount Rate',
      quarterTotalSavings: 'Quarterly Total Savings',
      optimizationOpportunities: 'Optimization Opportunities',
      anomalyDetection: 'Anomaly Detection',
      quarterlyTrend: 'Quarterly Discount Trend',
      top5ProductDiscount: 'TOP 5 Product Discount Rate',
      aiInsights: '🤖 AI Insights',
      generatingInsights: 'Generating insights...',
      months: 'months',
      instances: 'instances',
      monthsUnit: 'months',
      yearSavings: 'Annual Savings',
      fluctuation: 'Fluctuation',
      discountAmount: 'Discount Amount',
      discountRate: 'Discount Rate',
      avgDiscountRate: 'Average Discount Rate',
      momChange: 'MoM',
    },
    timeAnalysis: {
      quarterComparison: 'Quarter Comparison',
      yearlyComparison: 'Yearly Comparison',
      discountAnomaly: 'Discount Anomaly Detection',
      paidAmount: 'Paid Amount',
    },
    productAnalysis: {
      selectProducts: 'Select Products (Multi-select for comparison)',
      productTrendComparison: 'Product Discount Trend Comparison',
      productRanking: 'Product Detailed Ranking',
      productName: 'Product Name',
      totalConsumption: 'Total Consumption',
      totalDiscount: 'Total Discount',
      volatility: 'Volatility',
      trend: 'Trend',
    },
    regionAnalysis: {
      regionRanking: 'Region Discount Ranking',
      regionDetails: 'Region Detailed Data',
      region: 'Region',
      consumptionAmount: 'Consumption Amount',
      instanceCount: 'Instance Count',
      productCount: 'Product Count',
      percentage: 'Percentage',
    },
    billingAnalysis: {
      billingComparison: 'Billing Type Comparison',
      discountRateComparison: 'Discount Rate Comparison',
      subscriptionAdvantage: 'Subscription Discount Rate Advantage',
      subscriptionHigher: 'Subscription discount rate is higher by',
      optimizationSuggestions: 'Optimization Suggestions',
      instanceId: 'Instance ID',
      runningMonths: 'Running Months',
      currentDiscount: 'Current Discount',
      estimatedDiscount: 'Estimated Discount',
      annualSavings: 'Annual Savings',
      consumptionAmount: 'Consumption Amount',
      consumptionPercentage: 'Consumption Percentage',
    },
    advanced: {
      movingAverage: 'Discount Rate Moving Average (Smooth Trend)',
      cumulativeDiscount: 'Cumulative Discount Amount (Climbing Curve)',
      cumulativeTotal: 'Cumulative Total Discount',
      monthlyAverage: 'Monthly Average Discount',
      phase2Insights: 'Phase 2 Advanced Insights',
      trendSmoothing: 'Trend Smoothing',
      cumulativeSavings: 'Cumulative Savings',
      dataInsights: 'Data Insights',
      originalData: 'Original Data',
      monthMovingAverage: 'Month Moving Average',
      cumulativeDiscountAmount: 'Cumulative Discount',
      monthlyDiscount: 'Monthly Discount',
      rising: 'rising',
      falling: 'falling',
    },
  },
  costAnalysis: {
    title: 'Cost Analysis',
    description: 'View and analyze cloud resource costs',
    currentMonthCost: 'Current Month Cost',
    lastMonthCost: 'Last Month Cost',
    momGrowth: 'MoM Growth',
    yoyGrowth: 'YoY Growth',
    costBreakdown: 'Cost Breakdown',
    other: 'Other',
    viewAndAnalyze: 'View and analyze cloud resource costs',
  },
  accounts: {
    title: 'Account Management',
    description: 'Manage cloud account configurations',
    addAccount: 'Add Account',
    configuredAccounts: 'Configured Accounts',
    noAccounts: 'No accounts',
    noAccountsDesc: 'Please add cloud account configuration',
    region: 'Region',
    delete: 'Delete',
    confirmDelete: 'Confirm Delete',
    confirmDeleteMessage: 'Are you sure you want to delete account "{account}"? This action cannot be undone.',
    addCloudAccount: 'Add Cloud Account',
    addAccountDesc: 'You need to fill in the cloud provider\'s access key (AccessKey). It is recommended to use a RAM sub-account key with minimum permissions.',
    accountName: 'Account Name',
    accountNamePlaceholder: 'e.g.: zmyc',
    provider: 'Cloud Provider',
    aliyun: 'Alibaba Cloud (aliyun)',
    tencent: 'Tencent Cloud (tencent)',
    regionPlaceholder: 'e.g.: cn-hangzhou',
    accessKeyId: 'AccessKeyId',
    accessKeySecret: 'AccessKeySecret',
    secretNote: 'Secret will be saved to local config file/storage for backend to call cloud APIs.',
    hide: 'Hide',
    show: 'Show',
    nameRequired: 'Please enter account name (e.g.: zmyc)',
    keyIdRequired: 'Please enter AccessKeyId',
    secretRequired: 'Please enter AccessKeySecret',
    saving: 'Saving...',
    saveAndSwitch: 'Save and Switch',
  },
  optimization: {
    title: 'Optimization Suggestions',
    description: 'Detailed optimization suggestions based on resource analysis',
    noSuggestions: 'No optimization suggestions',
    noSuggestionsDesc: 'Current resource usage is good, no obvious optimization opportunities found',
    totalSavingsPotential: 'Total Savings Potential',
    monthlySavingsPotential: 'Monthly Savings Potential',
    suggestionCount: 'Suggestion Count',
    suggestions: 'suggestions',
    highPriority: 'High Priority',
    needImmediateAttention: 'Need Immediate Attention',
    mediumPriority: 'Medium Priority',
    suggestHandleSoon: 'Suggest Handle Soon',
    lowPriority: 'Low Priority',
    all: 'All',
    costOptimization: 'Cost Optimization',
    securityOptimization: 'Security Optimization',
    resourceManagement: 'Resource Management',
    relatedResources: 'Related Resources',
    savingsPotential: 'Savings Potential',
    optimizationSuggestion: 'Optimization Suggestion',
    unit: '',
    perMonth: '/month',
  },
  budget: {
    title: 'Budget Management',
    description: 'Create and manage cost budgets, monitor spending',
    budgetSettings: 'Budget Settings',
    monthlyBudget: 'Monthly Budget (CNY)',
    annualBudget: 'Annual Budget (CNY)',
    saveBudget: 'Save Budget',
    saving: 'Saving...',
    budgetUsage: 'Budget Usage',
    currentMonthUsed: 'Current Month Used',
    usageRate: 'Usage Rate',
    selectAccountFirst: 'Please select account first',
    saveSuccess: 'Budget settings saved successfully!',
    saveFailed: 'Save failed',
    deleteConfirm: 'Are you sure you want to delete this budget?',
    deleteFailed: 'Delete failed',
    createBudget: 'Create Budget',
    searchPlaceholder: 'Search budgets...',
    noBudgets: 'No budgets yet',
    noBudgetsDesc: 'Click "Create Budget" above to create your first budget',
    noMatchBudgets: 'No matching budgets found',
    tryOtherKeywords: 'Try using other keywords to search',
    budgetAmount: 'Budget Amount',
    spent: 'Spent',
    remaining: 'Remaining',
    usageProgress: 'Budget Usage Progress',
    days: 'days',
    predictedSpend: 'Predicted Spend',
    predictedOverspend: 'Predicted Overspend',
    alertTriggered: 'Alert Triggered',
    period: {
      monthly: 'Monthly',
      quarterly: 'Quarterly',
      yearly: 'Yearly',
    },
    scope: {
      total: 'Total Budget',
      tag: 'By Tag',
      service: 'By Service',
    },
  },
  reports: {
    title: 'Report Generation',
    description: 'Generate professional resource analysis reports in multiple formats and types',
    selectReportType: 'Select Report Type',
    selectFormat: 'Select Output Format',
    generateReport: 'Generate Report',
    selected: 'Selected',
    format: 'Format',
    reportType: 'Report Type',
    outputFormat: 'Output Format',
    generating: 'Generating report...',
    generateAndDownload: 'Generate and Download Report',
    tip: 'Tip',
    tipContent: 'Report generation may take a few minutes, please wait patiently. The report will be automatically downloaded when ready.',
    excelTip: ' Excel format is suitable for data analysis and further processing.',
    htmlTip: ' HTML format includes beautiful styles, suitable for online viewing and sharing.',
    pdfTip: ' PDF format is suitable for printing and archiving.',
    selectAccountFirst: 'Please select account first',
    generateSuccess: 'Report generated successfully!',
    generateFailed: 'Report generation failed',
    types: {
      comprehensive: {
        name: 'Comprehensive Report',
        description: 'Complete report including resource inventory, cost analysis, security checks and optimization suggestions',
      },
      resource: {
        name: 'Resource Inventory',
        description: 'Detailed resource list including configuration and status information for all cloud resources',
      },
      cost: {
        name: 'Cost Analysis',
        description: 'Detailed cost analysis report including cost trends, composition and optimization suggestions',
      },
      security: {
        name: 'Security Report',
        description: 'Security compliance check report including risk assessment and compliance analysis',
      },
    },
    formats: {
      excel: {
        name: 'Excel',
        description: 'Suitable for data analysis and further processing',
      },
      html: {
        name: 'HTML',
        description: 'Beautiful web format, suitable for online viewing and sharing',
      },
      pdf: {
        name: 'PDF',
        description: 'Professional document format, suitable for printing and archiving',
      },
    },
  },
  security: {
    title: 'Security Compliance',
    description: 'Comprehensive security checks and compliance analysis',
    securityScore: 'Security Score',
    publicExposure: 'Public Exposure',
    highRiskResources: 'High Risk Resources',
    diskEncryptionRate: 'Disk Encryption Rate',
    encrypted: 'Encrypted',
    tagCoverage: 'Tag Coverage',
    resourcesMissingTags: 'resources missing tags',
    securityImprovements: 'Security Improvement Suggestions',
    detailedResults: 'Detailed Security Check Results',
    foundIssues: 'Found',
    issues: 'issues',
    coverage: 'Coverage',
    encryptionRate: 'Encryption Rate',
    suggestion: 'Suggestion',
    problemResources: 'Problem Resources',
    region: 'Region',
    points: 'pts',
    ip: 'IP',
  },
  alerts: {
    title: 'Alert Management',
    description: 'Manage alert rules and view alert records',
    createRule: 'Create Alert Rule',
    rules: 'Alert Rules',
    records: 'Alert Records',
    alertRules: 'Alert Rules',
    manageRules: 'Configure and manage alert rules',
    noRules: 'No alert rules',
    noRulesDesc: 'Create your first alert rule to monitor cost anomalies',
    enabled: 'Enabled',
    disabled: 'Disabled',
    type: 'Type',
    metric: 'Metric',
    threshold: 'Threshold',
    check: 'Check',
    edit: 'Edit',
    delete: 'Delete',
    deleteConfirm: 'Are you sure you want to delete this alert rule?',
    deleteFailed: 'Delete failed',
    updateFailed: 'Update failed',
    checkFailed: 'Check failed',
    triggered: 'Triggered',
    acknowledged: 'Acknowledged',
    resolved: 'Resolved',
    closed: 'Closed',
    alertTriggered: 'Alert triggered',
    alertNotTriggered: 'Alert rule not triggered',
    triggerTime: 'Trigger Time',
    alertRecords: 'Alert Records',
    viewAndManageRecords: 'View and manage alert records',
    noRecords: 'No alert records',
    noRecordsDesc: 'Alert records will appear here when alert rules are triggered',
    rule: 'Rule',
    metricValue: 'Metric Value',
    confirm: 'Confirm',
    resolve: 'Resolve',
    close: 'Close',
    enable: 'Enable',
    disable: 'Disable',
    editRule: 'Edit Alert Rule',
    createRule: 'Create Alert Rule',
    configureRule: 'Configure alert rules and notification methods',
    alertType: 'Alert Type',
    costThreshold: 'Cost Threshold',
  },
}

// 中文翻译
const zh: Translations = {
  common: {
    loading: '加载中...',
    error: '错误',
    success: '成功',
    save: '保存',
    cancel: '取消',
    delete: '删除',
    edit: '编辑',
    add: '添加',
    search: '搜索',
    filter: '筛选',
    refresh: '刷新',
    export: '导出',
    confirm: '确认',
    close: '关闭',
    back: '返回',
    next: '下一步',
    previous: '上一步',
    apply: '应用',
    reset: '重置',
    select: '选择',
    all: '全部',
    none: '无',
    total: '总计',
    average: '平均',
    maximum: '最大',
    minimum: '最小',
    to: '至',
  },
  nav: {
    dashboard: '仪表盘',
    resources: '资源',
    costAnalysis: '成本分析',
    budget: '预算管理',
    customDashboards: '自定义仪表盘',
    discountAnalysis: '折扣分析',
    virtualTags: '虚拟标签',
    security: '安全',
    optimization: '优化',
    reports: '报告',
    settings: '设置',
  },
  dashboard: {
    title: '仪表盘',
    account: '账号',
    scanNow: '立即扫描',
    scanning: '扫描中...',
    totalCost: '总预估成本',
    monthlyEstimate: '本月预估支出',
    costTrend: '成本趋势',
    comparedToLastMonth: '较上月',
    idleResources: '闲置资源',
    suggestHandle: '建议尽快处理',
    totalResources: '资源总数',
    alertCount: '告警数量',
    needAttention: '需要关注',
    tagCoverage: '标签覆盖率',
    resourceTagCompleteness: '资源标签完整度',
    savingsPotential: '节省潜力',
    monthlySavingsPotential: '月度节省潜力',
    costTrendChart: '成本趋势',
    idleResourcesTable: '闲置资源',
    selectAccount: '请选择账号',
    selectAccountDesc: '请在左侧侧边栏选择要查看的云账号',
    goToAccountManagement: '前往账号管理',
  },
  cost: {
    title: '成本分析',
    currentMonth: '本月',
    lastMonth: '上月',
    costBreakdown: '成本构成',
    costTrend: '成本趋势',
    days: '天',
    all: '全部',
    custom: '自定义',
    startDate: '开始日期',
    endDate: '结束日期',
  },
  resources: {
    title: '资源管理',
    description: '查看和管理所有云资源',
    resourceList: '资源列表',
    nameId: '名称 / ID',
    type: '类型',
    status: '状态',
    region: '区域',
    spec: '规格',
    monthlyCost: '月度成本',
    createdTime: '创建时间',
    vpc: 'VPC',
    noResources: '未找到资源',
    searchPlaceholder: '搜索资源...',
    totalResources: '共 {total} 个资源，第 {page} / {totalPages} 页',
    page: '页',
    previousPage: '上一页',
    nextPage: '下一页',
  },
  settings: {
    title: '设置',
    accounts: '账号',
    rules: '规则',
    saveSuccess: '设置保存成功！',
    saveFailed: '保存失败',
  },
  dateRange: {
    all: '全部',
    last7Days: '7天',
    last30Days: '30天',
    last90Days: '90天',
    custom: '自定义',
    startDate: '开始日期',
    endDate: '结束日期',
    apply: '应用',
  },
  trend: {
    up: '上升',
    down: '下降',
    stable: '平稳',
    unknown: '未知',
    insufficientData: '数据不足',
  },
  discounts: {
    title: '折扣分析',
    description: '按产品 + 计费方式汇总折扣（包年包月 / 按量付费）',
    billingCycle: '账期',
    current: '当前',
    originalPrice: '原价(税前)',
    discountedPrice: '折后(税前)',
    savings: '节省',
    savingsDiscount: '节省 / 折扣',
    overallDiscount: '整体折扣',
    details: '明细',
    product: '产品',
    billingType: '计费方式',
    subscription: '包年包月',
    payAsYouGo: '按量付费',
    free: '免费',
    unpaid: '未结算',
    actualPaymentRate: '实付比例',
    searchPlaceholder: '搜索产品/代码...',
    loadCache: '加载缓存',
    forceRefresh: '强制刷新',
    loadingCache: '正在加载：优先读取缓存（更快）...',
    forceRefreshing: '正在强制刷新：拉取阿里云账单与折扣数据...',
    cancelRequest: '取消本次请求',
    loadFailed: '加载失败',
    timeoutMessage: '请求超时（已等待 {seconds}s）。可以先尝试"加载缓存"，或稍后再点"强制刷新"。',
    note: '说明：按量付费可能存在未结算金额（PaymentAmount=0），请结合"未结算"与"折后(税前)"理解。',
    all: '全部',
    waited: '已等待 {seconds}s',
  },
  discountAdvanced: {
    title: '高级折扣分析',
    description: '多维度深度分析 • 8大分析维度 • 自定义时间范围',
    exportExcel: '导出Excel',
    refresh: '刷新',
    loading: '正在加载高级折扣分析...',
    loadFailed: '加载失败',
    tabs: {
      overview: '总览',
      timeAnalysis: '时间分析',
      productAnalysis: '产品分析',
      regionAnalysis: '区域分析',
      billingAnalysis: '计费分析',
      advancedAnalysis: '高级分析',
    },
    overview: {
      latestQuarterDiscount: '最新季度折扣率',
      quarterTotalSavings: '季度总节省',
      optimizationOpportunities: '优化机会',
      anomalyDetection: '异常检测',
      quarterlyTrend: '季度折扣趋势',
      top5ProductDiscount: 'TOP 5产品折扣率',
      aiInsights: '🤖 AI智能洞察',
      generatingInsights: '正在生成智能洞察...',
      months: '个月',
      instances: '个实例',
      monthsUnit: '个月份',
      yearSavings: '年节省',
      fluctuation: '波动',
      discountAmount: '折扣金额',
      discountRate: '折扣率',
      avgDiscountRate: '平均折扣率',
      momChange: '环比',
    },
    timeAnalysis: {
      quarterComparison: '季度对比',
      yearlyComparison: '年度对比',
      discountAnomaly: '折扣异常检测',
      paidAmount: '实付金额',
    },
    productAnalysis: {
      selectProducts: '选择产品（多选对比）',
      productTrendComparison: '产品折扣趋势对比',
      productRanking: '产品详细排行',
      productName: '产品名称',
      totalConsumption: '总消费',
      totalDiscount: '总折扣',
      volatility: '波动率',
      trend: '趋势',
    },
    regionAnalysis: {
      regionRanking: '区域折扣排行',
      regionDetails: '区域详细数据',
      region: '区域',
      consumptionAmount: '消费金额',
      instanceCount: '实例数',
      productCount: '产品数',
      percentage: '占比',
    },
    billingAnalysis: {
      billingComparison: '计费方式对比',
      discountRateComparison: '折扣率对比',
      subscriptionAdvantage: '包年包月折扣率优势',
      subscriptionHigher: '包年包月折扣率高出',
      optimizationSuggestions: '优化建议',
      instanceId: '实例ID',
      runningMonths: '运行月数',
      currentDiscount: '当前折扣',
      estimatedDiscount: '预计折扣',
      annualSavings: '年节省',
      consumptionAmount: '消费金额',
      consumptionPercentage: '消费占比',
    },
    advanced: {
      movingAverage: '折扣率移动平均（平滑趋势）',
      cumulativeDiscount: '累计折扣金额（爬升曲线）',
      cumulativeTotal: '累计总折扣',
      monthlyAverage: '月均折扣',
      phase2Insights: 'Phase 2 高级洞察',
      trendSmoothing: '趋势平滑',
      cumulativeSavings: '累计节省',
      dataInsights: '数据洞察',
      originalData: '原始数据',
      monthMovingAverage: '月移动平均',
      cumulativeDiscountAmount: '累计折扣',
      monthlyDiscount: '月度折扣',
      rising: '上升',
      falling: '下降',
    },
  },
  costAnalysis: {
    title: '成本分析',
    description: '查看和分析云资源成本',
    currentMonthCost: '本月成本',
    lastMonthCost: '上月成本',
    momGrowth: '环比增长',
    yoyGrowth: '同比增长',
    costBreakdown: '成本构成',
    other: '其他',
    viewAndAnalyze: '查看和分析云资源成本',
  },
  accounts: {
    title: '账号管理',
    description: '管理云账号配置',
    addAccount: '添加账号',
    configuredAccounts: '已配置账号',
    noAccounts: '暂无账号',
    noAccountsDesc: '请添加云账号配置',
    region: '区域',
    delete: '删除',
    confirmDelete: '确认删除',
    confirmDeleteMessage: '确定要删除账号 "{account}" 吗？此操作不可恢复。',
    addCloudAccount: '添加云账号',
    addAccountDesc: '需要填写云厂商的访问密钥（AccessKey）。建议使用最小权限的 RAM 子账号密钥。',
    accountName: '账号名称',
    accountNamePlaceholder: '例如：zmyc',
    provider: '云厂商',
    aliyun: '阿里云（aliyun）',
    tencent: '腾讯云（tencent）',
    regionPlaceholder: '例如：cn-hangzhou',
    accessKeyId: 'AccessKeyId',
    accessKeySecret: 'AccessKeySecret',
    secretNote: 'Secret 将被保存到本地配置文件/存储中，用于后端调用云 API。',
    hide: '隐藏',
    show: '显示',
    nameRequired: '请输入账号名称（例如：zmyc）',
    keyIdRequired: '请输入 AccessKeyId',
    secretRequired: '请输入 AccessKeySecret',
    saving: '保存中...',
    saveAndSwitch: '保存并切换',
  },
  optimization: {
    title: '优化建议',
    description: '基于资源分析提供的详细优化建议',
    noSuggestions: '暂无优化建议',
    noSuggestionsDesc: '当前资源使用情况良好，未发现明显的优化机会',
    totalSavingsPotential: '总节省潜力',
    monthlySavingsPotential: '月度节省潜力',
    suggestionCount: '优化建议数',
    suggestions: '条优化建议',
    highPriority: '高优先级',
    needImmediateAttention: '需要立即关注',
    mediumPriority: '中优先级',
    suggestHandleSoon: '建议尽快处理',
    lowPriority: '低优先级',
    all: '全部',
    costOptimization: '成本优化',
    securityOptimization: '安全优化',
    resourceManagement: '资源管理',
    relatedResources: '相关资源',
    savingsPotential: '节省潜力',
    optimizationSuggestion: '优化建议',
    unit: '个',
    perMonth: '/月',
  },
  budget: {
    title: '预算管理',
    description: '创建和管理成本预算，监控支出情况',
    budgetSettings: '预算设置',
    monthlyBudget: '月度预算 (CNY)',
    annualBudget: '年度预算 (CNY)',
    saveBudget: '保存预算',
    saving: '保存中...',
    budgetUsage: '预算使用情况',
    currentMonthUsed: '本月已使用',
    usageRate: '使用率',
    selectAccountFirst: '请先选择账号',
    saveSuccess: '预算设置成功！',
    saveFailed: '保存失败',
    deleteConfirm: '确定要删除这个预算吗？',
    deleteFailed: '删除失败',
    createBudget: '新建预算',
    searchPlaceholder: '搜索预算...',
    noBudgets: '还没有预算',
    noBudgetsDesc: '点击上方"新建预算"按钮创建第一个预算',
    noMatchBudgets: '未找到匹配的预算',
    tryOtherKeywords: '尝试使用其他关键词搜索',
    budgetAmount: '预算金额',
    spent: '已支出',
    remaining: '剩余预算',
    usageProgress: '预算使用进度',
    days: '天',
    predictedSpend: '预测支出',
    predictedOverspend: '预计超支',
    alertTriggered: '已触发告警',
    period: {
      monthly: '月度',
      quarterly: '季度',
      yearly: '年度',
    },
    scope: {
      total: '总预算',
      tag: '按标签',
      service: '按服务',
    },
  },
  reports: {
    title: '报告生成',
    description: '生成专业的资源分析报告，支持多种格式和类型',
    selectReportType: '选择报告类型',
    selectFormat: '选择输出格式',
    generateReport: '生成报告',
    selected: '已选择',
    format: '格式',
    reportType: '报告类型',
    outputFormat: '输出格式',
    generating: '正在生成报告...',
    generateAndDownload: '生成并下载报告',
    tip: '提示',
    tipContent: '报告生成可能需要几分钟时间，请耐心等待。生成完成后将自动下载。',
    excelTip: ' Excel 格式适合数据分析和进一步处理。',
    htmlTip: ' HTML 格式包含精美的样式，适合在线查看和分享。',
    pdfTip: ' PDF 格式适合打印和归档保存。',
    selectAccountFirst: '请先选择账号',
    generateSuccess: '报告生成成功！',
    generateFailed: '报告生成失败',
    types: {
      comprehensive: {
        name: '综合报告',
        description: '包含资源清单、成本分析、安全检查和优化建议的完整报告',
      },
      resource: {
        name: '资源清单',
        description: '详细的资源列表，包括所有云资源的配置和状态信息',
      },
      cost: {
        name: '成本分析',
        description: '详细的成本分析报告，包括成本趋势、构成和优化建议',
      },
      security: {
        name: '安全报告',
        description: '安全合规检查报告，包括风险评估和合规性分析',
      },
    },
    formats: {
      excel: {
        name: 'Excel',
        description: '适合数据分析和进一步处理',
      },
      html: {
        name: 'HTML',
        description: '精美的网页格式，适合在线查看和分享',
      },
      pdf: {
        name: 'PDF',
        description: '专业的文档格式，适合打印和归档',
      },
    },
  },
  security: {
    title: '安全合规',
    description: '全面的安全检查和合规性分析',
    securityScore: '安全评分',
    publicExposure: '公网暴露',
    highRiskResources: '高风险资源',
    diskEncryptionRate: '磁盘加密率',
    encrypted: '已加密',
    tagCoverage: '标签覆盖率',
    resourcesMissingTags: '个资源缺失标签',
    securityImprovements: '安全改进建议',
    detailedResults: '详细安全检查结果',
    foundIssues: '发现',
    issues: '个问题',
    coverage: '覆盖率',
    encryptionRate: '加密率',
    suggestion: '建议',
    problemResources: '问题资源',
    region: '区域',
    points: '分',
    ip: 'IP',
  },
  alerts: {
    title: '告警管理',
    description: '管理告警规则和查看告警记录',
    createRule: '新建告警规则',
    rules: '告警规则',
    records: '告警记录',
    alertRules: '告警规则',
    manageRules: '配置和管理告警规则',
    noRules: '暂无告警规则',
    noRulesDesc: '创建第一个告警规则来监控成本异常',
    enabled: '已启用',
    disabled: '已禁用',
    type: '类型',
    metric: '指标',
    threshold: '阈值',
    check: '检查',
    edit: '编辑',
    delete: '删除',
    deleteConfirm: '确定要删除此告警规则吗？',
    deleteFailed: '删除失败',
    updateFailed: '更新失败',
    checkFailed: '检查失败',
    triggered: '已触发',
    acknowledged: '已确认',
    resolved: '已解决',
    closed: '已关闭',
    alertTriggered: '告警已触发',
    alertNotTriggered: '告警规则未触发',
    triggerTime: '触发时间',
    alertRecords: '告警记录',
    viewAndManageRecords: '查看和管理告警记录',
    noRecords: '暂无告警记录',
    noRecordsDesc: '当告警规则触发时，告警记录将显示在这里',
    rule: '规则',
    metricValue: '指标值',
    confirm: '确认',
    resolve: '解决',
    close: '关闭',
    enable: '启用',
    disable: '禁用',
    editRule: '编辑告警规则',
    createRule: '新建告警规则',
    configureRule: '配置告警规则和通知方式',
    alertType: '告警类型',
    costThreshold: '成本阈值',
  },
}

const translations: Record<Locale, Translations> = {
  en,
  zh,
}

export function getTranslations(locale: Locale): Translations {
  return translations[locale] || translations[defaultLocale]
}

export function t(locale: Locale, key: string): string {
  const keys = key.split('.')
  let value: any = translations[locale] || translations[defaultLocale]
  
  for (const k of keys) {
    value = value?.[k]
    if (value === undefined) {
      // Fallback to default locale
      value = translations[defaultLocale]
      for (const k2 of keys) {
        value = value?.[k2]
      }
      break
    }
  }
  
  return typeof value === 'string' ? value : key
}
