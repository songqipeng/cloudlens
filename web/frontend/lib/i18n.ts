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
    timeout: string
    timeoutTitle: string
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
    avgDailyCost: string
    maxDailyCost: string
    minDailyCost: string
    trend: string
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
    scanFailed: string
    loading: string
    loadingDesc: string
    loadingSummary: string
    loadingIdle: string
    loadingTrend: string
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
  
  // Dashboard View
  dashboardView: {
    saveFailed: string
    dashboardNotFound: string
    backToList: string
    back: string
    cancel: string
    save: string
    editLayout: string
    editModeHint: string
  }
  
  // CIS
  cis: {
    title: string
    description: string
    complianceRate: string
    checks: string
    noChecks: string
    loading: string
  }
  
  // Discount Trend
  discountTrend: {
    title: string
    description: string
    trendUp: string
    trendDown: string
    productName: string
    totalDiscount: string
    avgDiscountRate: string
    latestDiscountRate: string
    discountRateChange: string
    trend: string
    instanceId: string
    instanceName: string
    product: string
    officialPrice: string
    discountAmount: string
    discountRate: string
    payableAmount: string
    loadFailed: string
    showAllHistory: string
    showRecentMonths: string
    months: string
    loadCache: string
    forceRefresh: string
    timeRange: string
    last3Months: string
    last6Months: string
    last1Year: string
    allTime: string
    customRange: string
    startMonth: string
    endMonth: string
    apply: string
    analyzing: string
    possibleReasons: string
    noBillData: string
    runCommand: string
    waitSync: string
    contactAdmin: string
    latestDiscountRateTitle: string
    vsFirstMonth: string
    avgDiscountRateTitle: string
    recentMonths: string
    discountTrendTitle: string
    range: string
    cumulativeSavingsTitle: string
    tabs: {
      overview: string
      products: string
      contracts: string
      instances: string
    }
    discountRateTrend: string
    discountRateUnit: string
    discountAmountComparison: string
    amountUnit: string
    productAnalysis: string
    contractAnalysis: string
    topInstances: string
    cumulativeSavings: string
    avgDiscountRateLabel: string
    latestDiscountRateLabel: string
    coverageMonths: string
    monthsUnit: string
    noData: string
  }
  
  // Cost Allocation
  costAllocation: {
    title: string
    description: string
    rules: string
    results: string
    rulesTitle: string
    rulesDescription: string
    noRules: string
    noRulesDesc: string
    noResults: string
    noResultsDesc: string
    createRule: string
    editRule: string
    deleteConfirm: string
    deleteFailed: string
    executeSuccess: string
    executeFailed: string
    saveFailed: string
    configureRule: string
    ruleName: string
    ruleDescription: string
    allocationMethod: string
    allocationTarget: string
    allocationTargetPlaceholder: string
    add: string
    weight: string
    enableRule: string
    enabled: string
    disabled: string
    execute: string
    period: string
    totalCost: string
    allocated: string
    unallocated: string
    allocationRate: string
    allocationDetails: string
    methods: {
      equal: string
      proportional: string
      usage_based: string
      tag_based: string
      custom: string
    }
  }
  
  // Virtual Tags
  virtualTags: {
    title: string
    description: string
    noTags: string
    noTagsDesc: string
    noMatchTags: string
    tryOtherKeywords: string
    createTag: string
    editTag: string
    searchPlaceholder: string
    deleteConfirm: string
    deleteFailed: string
    selectAccountFirst: string
    fillRequiredFields: string
    atLeastOneRule: string
    saveFailed: string
    previewFailed: string
    previewMatchingResources: string
    ruleCount: string
    moreRules: string
    configureTagRules: string
    tagName: string
    tagKey: string
    tagValue: string
    priority: string
    priorityDesc: string
    field: string
    operator: string
    pattern: string
    matchingRules: string
    addRule: string
    rule: string
    exampleProduction: string
    exampleEnvironment: string
    exampleProd: string
    resourceName: string
    region: string
    resourceType: string
    instanceId: string
    contains: string
    equals: string
    startsWith: string
    endsWith: string
    regex: string
    saving: string
    previewTitle: string
    previewDescription: string
    matchedResources: string
    totalResources: string
    matchRate: string
    matchingRulesLabel: string
    resourceList: string
    resourceListMax: string
    resourceId: string
    name: string
    status: string
    spec: string
    noMatchedResources: string
    previewDataEmpty: string
  }
  
  // Custom Dashboards
  customDashboards: {
    title: string
    description: string
    noDashboards: string
    noDashboardsDesc: string
    noMatchDashboards: string
    tryOtherKeywords: string
    createDashboard: string
    editDashboard: string
    searchPlaceholder: string
    noWidgets: string
    deleteFailed: string
    saveFailed: string
    deleteConfirm: string
    gridLayout: string
    freeLayout: string
    widgets: string
    widgetsUnit: string
    updatedAt: string
    createdAt: string
    view: string
    shared: string
    dashboardName: string
    dashboardDescription: string
    layoutType: string
    shareDashboard: string
    widgetList: string
    addMetric: string
    addChart: string
    addTable: string
    widgetTitle: string
    metric: string
    chart: string
    table: string
    cancel: string
    save: string
  }
  
  // Budgets (extended)
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
    editBudget: string
    newBudget: string
    configureBudget: string
    budgetName: string
    budgetAmountLabel: string
    budgetPeriod: string
    budgetType: string
    startDate: string
    alertRules: string
    addAlert: string
    enable: string
    noAlertRules: string
    noAlertRulesDesc: string
    cancel: string
    save: string
    spendingTrend: string
    date: string
    spending: string
    thresholdTriggered: string
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
  
  // Reports (extended)
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
    recentReports: string
    download: string
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
  
  // Settings
  settings: {
    title: string
    accounts: string
    rules: string
    saveSuccess: string
    saveFailed: string
    saving: string
    idleRules: {
      title: string
      description: string
      cpuThreshold: string
      cpuThresholdDesc: string
      excludeTags: string
      excludeTagsDesc: string
    }
    notifications: {
      title: string
      description: string
      senderEmail: string
      senderEmailDesc: string
      authCode: string
      qqMailNote: string
      gmailNote: string
      qqMailLink: string
      defaultReceiverEmail: string
      defaultReceiverEmailDesc: string
      smtpInfo: string
      server: string
      port: string
    }
    language: {
      title: string
      description: string
      currentLanguage: string
      chinese: string
      english: string
    }
    about: {
      title: string
      description: string
      version: string
      desc: string
      descriptionText: string
      platformName: string
    }
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
    discountUnit: string
    discountOff: string
    selectAccountFirst: string
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
      totalCost: string
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
      movingAverageDesc: string
      threeMonthDesc: string
      sixMonthDesc: string
      twelveMonthDesc: string
      trendDesc: string
      trend: string
      cumulativeSavingsDesc: string
      dataInsightsDesc: string
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
    totalCost: string
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
    editAccount: string
    editAccountDesc: string
    editSecretPlaceholder: string
    editSecretNote: string
    editNameNote: string
    confirmNameChange: string
    alias: string
    aliasPlaceholder: string
    aliasNote: string
    accountNameImmutable: string
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
    loadingProgress: string
    analyzingProgress: string
    loadingProgressDesc: string
    timeoutMessage: string
    refresh: string
    unit: string
    perMonth: string
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
    configureRule: string
    alertType: string
    costThreshold: string
    ruleName: string
    ruleDescription: string
    severity: string
    condition: string
    notificationChannels: string
    notificationChannelsDesc: string
    receiverEmail: string
    receiverEmailDesc: string
    receiverEmailDescNoDefault: string
    webhookNotification: string
    webhookNotificationDesc: string
    enableRule: string
    budgetOverspend: string
    resourceAnomaly: string
    securityCompliance: string
    info: string
    warning: string
    error: string
    critical: string
    totalCost: string
    dailyCost: string
    monthlyCost: string
    greaterThan: string
    greaterThanOrEqual: string
    lessThan: string
    lessThanOrEqual: string
    notificationChannelsLabel: string
    noChannelsWarning: string
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
    timeout: 'Request timeout, please try again later',
    timeoutTitle: 'Request Timeout',
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
    avgDailyCost: 'Average Daily Cost',
    maxDailyCost: 'Maximum Daily Cost',
    minDailyCost: 'Minimum Daily Cost',
    trend: 'Trend',
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
    scanFailed: 'Scan failed',
    loading: 'Loading Dashboard...',
    loadingDesc: 'Fetching the latest data from the cloud, please wait...',
    loadingSummary: 'Loading summary data...',
    loadingIdle: 'Loading idle resources...',
    loadingTrend: 'Loading cost trends...',
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
    saving: 'Saving...',
    idleRules: {
      title: 'Idle Detection Rules (ECS)',
      description: 'Define when an instance is considered idle',
      cpuThreshold: 'CPU Threshold (%)',
      cpuThresholdDesc: 'Instances with average CPU usage below this value will be marked as idle',
      excludeTags: 'Exclude Tags (comma-separated)',
      excludeTagsDesc: 'Resources with these tags will be ignored',
    },
    notifications: {
      title: 'Notification Settings',
      description: 'Configure email notifications for alerts. SMTP server will be auto-configured based on email type.',
      senderEmail: 'Sender Email Address',
      senderEmailDesc: 'Supports QQ Mail, Gmail, 163 Mail, etc. SMTP server will be auto-configured.',
      authCode: 'Authorization Code / Password',
      qqMailNote: '• QQ Mail: Enable SMTP service in QQ Mail settings and get authorization code',
      gmailNote: '• Gmail: Use app-specific password (App Password)',
      qqMailLink: 'How to get QQ Mail authorization code?',
      defaultReceiverEmail: 'Default Receiver Email',
      defaultReceiverEmailDesc: 'Default email address to receive alert notifications. If a rule doesn\'t specify a receiver email, this default will be used.',
      smtpInfo: 'Auto-configured SMTP settings:',
      server: 'Server: ',
      port: 'Port: ',
    },
    language: {
      title: 'Language Settings',
      description: 'Select interface display language',
      currentLanguage: 'Current Language',
      chinese: 'English',
      english: 'English',
    },
    about: {
      title: 'About',
      description: 'CloudLens Version Information',
      version: 'Version',
      desc: 'Description',
      descriptionText: 'CloudLens is an enterprise-grade multi-cloud resource governance and analysis tool that helps you optimize cloud resource usage and reduce costs.',
      platformName: 'Multi-Cloud Resource Governance Platform',
    },
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
    discountUnit: 'Discount Unit',
    discountOff: 'Discount Off',
    selectAccountFirst: 'Please select account first',
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
      totalCost: 'Total Cost',
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
      movingAverageDesc: 'Moving average can smooth short-term fluctuations and show long-term trends:',
      threeMonthDesc: '3-month moving average: reflects short-term trends',
      sixMonthDesc: '6-month moving average: reflects medium-term trends',
      twelveMonthDesc: '12-month moving average: reflects long-term trends',
      trendDesc: 'shows discount rate',
      trend: 'trend',
      cumulativeSavingsDesc: 'cumulative savings',
      dataInsightsDesc: 'Phase 2 provides deeper trend analysis and data visualization',
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
    totalCost: 'Total Cost',
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
    editAccount: 'Edit Account',
    editAccountDesc: 'Update account configuration. Leave secret blank to keep existing secret.',
    editSecretPlaceholder: 'Leave blank to keep existing secret',
    editSecretNote: 'Leave blank to keep existing secret, enter new secret to replace existing one',
    editNameNote: 'Changing the account name will automatically migrate all related data to ensure correct associations.',
    confirmNameChange: 'Are you sure you want to change the account name from "{old}" to "{new}"? The system will automatically update all related data.',
    alias: 'Display Alias',
    aliasPlaceholder: 'Optional, used for display. Leave blank to show account name.',
    aliasNote: 'After setting an alias, the interface will display the alias instead of the account name, but data associations still use the account name.',
    accountNameImmutable: 'Account name cannot be modified and is used for data associations.',
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
    loadingProgress: 'Loading optimization suggestions...',
    analyzingProgress: 'Analyzing resource usage, this may take 30-60 seconds...',
    loadingProgressDesc: 'First load may take longer, please wait...',
    timeoutMessage: 'Calculation takes longer, suggest using cached data or retry later',
    refresh: 'Refresh',
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
    configureRule: 'Configure alert rules and notification methods',
    alertType: 'Alert Type',
    costThreshold: 'Cost Threshold',
    ruleName: 'Rule Name',
    ruleDescription: 'Description',
    severity: 'Severity',
    condition: 'Condition',
    notificationChannels: 'Notification Channels',
    notificationChannelsDesc: 'Configure notification methods when alerts are triggered. At least one channel must be configured, otherwise alerts will not be sent.',
    receiverEmail: '📧 Receiver Email',
    receiverEmailDesc: 'Leave empty to use default: {email}',
    receiverEmailDescNoDefault: 'Email address to receive alert notifications. Configure default receiver email in system settings.',
    webhookNotification: '🔗 Webhook Notification',
    webhookNotificationDesc: 'A POST request with alert details in JSON format will be sent to this URL when alert is triggered',
    enableRule: 'Enable this rule',
    budgetOverspend: 'Budget Overspend',
    resourceAnomaly: 'Resource Anomaly',
    securityCompliance: 'Security Compliance',
    info: 'Info',
    warning: 'Warning',
    error: 'Error',
    critical: 'Critical',
    totalCost: 'Total Cost',
    dailyCost: 'Daily Cost',
    monthlyCost: 'Monthly Cost',
    greaterThan: 'Greater Than',
    greaterThanOrEqual: 'Greater Than or Equal',
    lessThan: 'Less Than',
    lessThanOrEqual: 'Less Than or Equal',
    notificationChannelsLabel: 'Notification Channels:',
    noChannelsWarning: 'No notification channels configured, alerts will not be sent',
  },
  customDashboards: {
    title: 'Custom Dashboards',
    description: 'Create and manage custom dashboards',
    noDashboards: 'No custom dashboards yet',
    noDashboardsDesc: 'Click "Create Dashboard" above to create your first dashboard',
    noMatchDashboards: 'No matching dashboards found',
    tryOtherKeywords: 'Try using other keywords to search',
    createDashboard: 'Create Dashboard',
    editDashboard: 'Edit Dashboard',
    searchPlaceholder: 'Search dashboards...',
    noWidgets: 'No widgets yet, click the button above to add',
    deleteFailed: 'Delete failed',
    saveFailed: 'Save failed',
    deleteConfirm: 'Are you sure you want to delete this dashboard?',
    gridLayout: 'Grid Layout',
    freeLayout: 'Free Layout',
    widgets: 'widgets',
    widgetsUnit: 'widgets',
    updatedAt: 'Updated on',
    createdAt: 'Created on',
    view: 'View',
    shared: 'Shared',
    dashboardName: 'Dashboard Name',
    dashboardDescription: 'Description',
    layoutType: 'Layout Type',
    shareDashboard: 'Share Dashboard',
    widgetList: 'Widget List',
    addMetric: '+ Metric',
    addChart: '+ Chart',
    addTable: '+ Table',
    widgetTitle: 'Widget Title',
    metric: '📊 Metric',
    chart: '📈 Chart',
    table: '📋 Table',
    cancel: 'Cancel',
    save: 'Save',
  },
  virtualTags: {
    title: 'Virtual Tags',
    description: 'Create virtual tags through rule engine for cost allocation and grouping without modifying actual cloud resource tags',
    noTags: 'No virtual tags yet',
    noTagsDesc: 'Click "Create Tag" above to create your first virtual tag',
    noMatchTags: 'No matching tags found',
    tryOtherKeywords: 'Try other search terms',
    createTag: 'Create Tag',
    editTag: 'Edit Tag',
    searchPlaceholder: 'Search tag name, key or value...',
    deleteConfirm: 'Are you sure you want to delete this tag?',
    deleteFailed: 'Delete failed',
    selectAccountFirst: 'Please select account first',
    fillRequiredFields: 'Please fill in all required fields',
    atLeastOneRule: 'At least one valid rule is required',
    saveFailed: 'Save failed',
    previewFailed: 'Preview failed',
    previewMatchingResources: 'Preview Matching Resources',
    ruleCount: 'Rule Count',
    priority: 'Priority',
    moreRules: 'more rules...',
    configureTagRules: 'Configure tag rules for matching cloud resources',
    tagName: 'Tag Name',
    tagKey: 'Tag Key',
    tagValue: 'Tag Value',
    priorityDesc: 'Higher numbers have higher priority',
    field: 'Field',
    operator: 'Operator',
    pattern: 'Pattern',
    matchingRules: 'Matching Rules',
    addRule: 'Add Rule',
    rule: 'Rule',
    exampleProduction: 'e.g.: Production Environment',
    exampleEnvironment: 'e.g.: environment',
    exampleProd: 'e.g.: prod',
    resourceName: 'Resource Name',
    region: 'Region',
    resourceType: 'Resource Type',
    instanceId: 'Instance ID',
    contains: 'Contains',
    equals: 'Equals',
    startsWith: 'Starts With',
    endsWith: 'Ends With',
    regex: 'Regex',
    saving: 'Saving...',
    previewTitle: 'Tag Preview',
    previewDescription: 'View matching resource list',
    matchedResources: 'Matched Resources',
    totalResources: 'Total Resources',
    matchRate: 'Match Rate',
    matchingRulesLabel: 'Matching Rules',
    resourceList: 'Matching Resource List',
    resourceListMax: 'Matching Resource List (max 100)',
    resourceId: 'Resource ID',
    name: 'Name',
    status: 'Status',
    spec: 'Spec',
    noMatchedResources: 'No matched resources',
    previewDataEmpty: 'Preview data is empty',
  },
  costAllocation: {
    title: 'Cost Allocation',
    description: 'Manage cost allocation rules and view allocation results',
    rules: 'Allocation Rules',
    results: 'Allocation Results',
    rulesTitle: 'Cost Allocation Rules',
    rulesDescription: 'Configure and manage cost allocation rules',
    noRules: 'No cost allocation rules yet',
    noRulesDesc: 'Create your first cost allocation rule to allocate shared costs',
    noResults: 'No allocation results yet',
    noResultsDesc: 'After executing cost allocation rules, results will be displayed here',
    createRule: 'Create Rule',
    editRule: 'Edit Rule',
    deleteConfirm: 'Are you sure you want to delete this cost allocation rule?',
    deleteFailed: 'Delete failed',
    executeSuccess: 'Cost allocation executed successfully',
    executeFailed: 'Execution failed',
    saveFailed: 'Save failed',
    configureRule: 'Configure Cost Allocation Rule',
    ruleName: 'Rule Name',
    ruleDescription: 'Description',
    allocationMethod: 'Allocation Method',
    allocationTarget: 'Allocation Target',
    allocationTargetPlaceholder: 'Enter target name (e.g., department, project)',
    add: 'Add',
    weight: 'Weight',
    enableRule: 'Enable this rule',
    enabled: 'Enabled',
    disabled: 'Disabled',
    execute: 'Execute',
    period: 'Period',
    totalCost: 'Total Cost',
    allocated: 'Allocated',
    unallocated: 'Unallocated',
    allocationRate: 'Allocation Rate',
    allocationDetails: 'Allocation Details',
    methods: {
      equal: 'Equal Allocation',
      proportional: 'Proportional Allocation',
      usage_based: 'Usage-based Allocation',
      tag_based: 'Tag-based Allocation',
      custom: 'Custom Rule',
    },
  },
  dashboardView: {
    saveFailed: 'Save failed',
    dashboardNotFound: 'Dashboard not found',
    backToList: 'Back to List',
    back: 'Back',
    cancel: 'Cancel',
    save: 'Save',
    editLayout: 'Edit Layout',
    editModeHint: '💡 Edit mode: Drag widgets to adjust position and size, then click "Save" when done',
  },
  cis: {
    title: 'CIS Compliance Check',
    description: 'CIS Benchmark compliance check',
    complianceRate: 'Compliance Rate',
    checks: 'Checks',
    noChecks: 'No checks available',
    loading: 'Loading...',
  },
  discountTrend: {
    title: 'Discount Trend Analysis',
    description: 'Analyze discount trends and patterns',
    trendUp: 'Rising',
    trendDown: 'Falling',
    productName: 'Product Name',
    totalDiscount: 'Total Discount',
    avgDiscountRate: 'Average Discount Rate',
    latestDiscountRate: 'Latest Discount Rate',
    discountRateChange: 'Discount Rate Change',
    trend: 'Trend',
    instanceId: 'Instance ID',
    instanceName: 'Instance Name',
    product: 'Product',
    officialPrice: 'Official Price',
    discountAmount: 'Discount Amount',
    discountRate: 'Discount Rate',
    payableAmount: 'Payable Amount',
    loadFailed: 'Load Failed',
    showAllHistory: 'Show all historical data',
    showRecentMonths: 'Show recent {months} months',
    months: 'months',
    loadCache: 'Load Cache',
    forceRefresh: 'Force Refresh',
    timeRange: 'Time Range',
    last3Months: 'Last 3 Months',
    last6Months: 'Last 6 Months',
    last1Year: 'Last 1 Year',
    allTime: 'All Time',
    customRange: 'Custom Range',
    startMonth: 'Start Month',
    endMonth: 'End Month',
    apply: 'Apply',
    analyzing: 'Analyzing billing data...',
    possibleReasons: 'Possible reasons:',
    noBillData: 'No billing data for this account in the database',
    runCommand: 'Please run billing fetch command first: ./cl bill fetch --account ydzn --use-db',
    waitSync: 'Or wait for automatic billing sync task to complete',
    contactAdmin: 'If the problem persists, please contact the administrator',
    latestDiscountRateTitle: 'Latest Discount Rate',
    vsFirstMonth: 'vs First Month',
    avgDiscountRateTitle: 'Average Discount Rate',
    recentMonths: 'Recent {count} months',
    discountTrendTitle: 'Discount Trend',
    range: 'Range:',
    cumulativeSavingsTitle: 'Cumulative Savings',
    tabs: {
      overview: 'Trend Overview',
      products: 'Product Analysis',
      contracts: 'Contract Analysis',
      instances: 'TOP Instances',
    },
    discountRateTrend: 'Discount Rate Trend',
    discountRateUnit: 'Discount Rate (%)',
    discountAmountComparison: 'Discount Amount vs Official Price',
    amountUnit: 'Amount (¥)',
    productAnalysis: 'Product Discount Analysis (TOP 20)',
    contractAnalysis: 'Contract Discount Analysis (TOP 10)',
    topInstances: 'High Discount Instances TOP 50 (Last Month)',
    cumulativeSavings: 'Cumulative Savings',
    avgDiscountRateLabel: 'Average Discount Rate',
    latestDiscountRateLabel: 'Latest Discount Rate',
    coverageMonths: 'Coverage Months',
    monthsUnit: 'months',
    noData: 'No discount trend data available',
  },
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
    editBudget: 'Edit Budget',
    newBudget: 'New Budget',
    configureBudget: 'Configure budget information and alert rules',
    budgetName: 'Budget Name',
    budgetAmountLabel: 'Budget Amount (CNY)',
    budgetPeriod: 'Budget Period',
    budgetType: 'Budget Type',
    startDate: 'Start Date',
    alertRules: 'Alert Rules',
    addAlert: 'Add Alert',
    enable: 'Enable',
    noAlertRules: 'No alert rules',
    noAlertRulesDesc: 'No alert rules yet, click "Add Alert" to add',
    cancel: 'Cancel',
    save: 'Save',
    spendingTrend: 'Spending Trend',
    date: 'Date:',
    spending: 'Spending',
    thresholdTriggered: 'threshold triggered',
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
    timeout: '请求超时，请稍后重试',
    timeoutTitle: '请求超时',
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
    avgDailyCost: '日均成本',
    maxDailyCost: '最高日成本',
    minDailyCost: '最低日成本',
    trend: '趋势',
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
    scanFailed: '扫描失败',
    loading: '正在加载仪表盘...',
    loadingDesc: '正在从云端获取最新数据，请稍候...',
    loadingSummary: '正在加载摘要数据...',
    loadingIdle: '正在加载闲置资源...',
    loadingTrend: '正在加载成本趋势...',
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
    saving: '保存中...',
    idleRules: {
      title: '闲置检测规则 (ECS)',
      description: '定义什么情况下判定为闲置实例',
      cpuThreshold: 'CPU阈值 (%)',
      cpuThresholdDesc: '平均CPU使用率低于此值的实例将被标记为闲置',
      excludeTags: '排除标签 (逗号分隔)',
      excludeTagsDesc: '带有这些标签的资源将被忽略',
    },
    notifications: {
      title: '通知配置',
      description: '配置邮件通知，用于发送告警通知。系统会根据邮箱类型自动配置SMTP服务器。',
      senderEmail: '发件邮箱',
      senderEmailDesc: '支持QQ邮箱、Gmail、163邮箱等。系统会自动配置对应的SMTP服务器。',
      authCode: '授权码/密码',
      qqMailNote: '• QQ邮箱：需要在QQ邮箱设置中开启SMTP服务并获取授权码',
      gmailNote: '• Gmail：需要使用应用专用密码（App Password）',
      qqMailLink: 'QQ邮箱如何获取授权码？',
      defaultReceiverEmail: '默认接收邮箱',
      defaultReceiverEmailDesc: '告警通知的默认接收邮箱。在创建告警规则时，如果没有指定接收邮箱，将使用此默认邮箱。',
      smtpInfo: '自动配置的SMTP信息：',
      server: '服务器：',
      port: '端口：',
    },
    language: {
      title: '语言设置',
      description: '选择界面显示语言',
      currentLanguage: '当前语言',
      chinese: '中文',
      english: 'English',
    },
    about: {
      title: '关于',
      description: 'CloudLens 版本信息',
      version: '版本',
      desc: '描述',
      descriptionText: 'CloudLens 是一个企业级多云资源治理与分析工具，帮助您优化云资源使用，降低成本。',
      platformName: '多云资源治理平台',
    },
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
    discountUnit: '折',
    discountOff: '折',
    selectAccountFirst: '请先选择账号',
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
      totalCost: '总成本',
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
      movingAverageDesc: '移动平均可以平滑短期波动，显示长期趋势：',
      threeMonthDesc: '3月移动平均：反映短期趋势',
      sixMonthDesc: '6月移动平均：反映中期趋势',
      twelveMonthDesc: '12月移动平均：反映长期趋势',
      trendDesc: '显示折扣率整体',
      trend: '趋势',
      cumulativeSavingsDesc: '累计节省',
      dataInsightsDesc: 'Phase 2提供更深入的趋势分析和数据可视化',
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
    totalCost: '总成本',
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
    editAccount: '编辑账号',
    editAccountDesc: '更新账号配置信息。如果不输入新密钥，将保持现有密钥不变。',
    editSecretPlaceholder: '留空则不更新密钥',
    editSecretNote: '留空则不更新密钥，输入新密钥将替换现有密钥',
    editNameNote: '修改名称后，系统会自动迁移所有相关数据，确保数据关联正确',
    confirmNameChange: '确定要将账号名称从 "{old}" 更改为 "{new}" 吗？系统会自动更新所有相关数据。',
    alias: '显示别名',
    aliasPlaceholder: '可选，用于显示，留空则显示账号名称',
    aliasNote: '设置别名后，界面将显示别名而不是账号名称，但数据关联仍使用账号名称',
    accountNameImmutable: '账号名称不可修改，用于数据关联',
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
    loadingProgress: '正在加载优化建议...',
    analyzingProgress: '正在分析资源使用情况，这可能需要30-60秒...',
    loadingProgressDesc: '首次加载可能需要较长时间，请耐心等待...',
    timeoutMessage: '计算时间较长，建议使用缓存数据或稍后重试',
    refresh: '刷新',
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
    configureRule: '配置告警规则和通知方式',
    alertType: '告警类型',
    costThreshold: '成本阈值',
    ruleName: '规则名称',
    description: '描述',
    severity: '严重程度',
    condition: '条件',
    notificationChannels: '通知渠道配置',
    notificationChannelsDesc: '配置告警触发时的通知方式。至少需要配置一个通知渠道，否则告警将不会发送。',
    receiverEmail: '📧 接收邮箱',
    receiverEmailDesc: '留空将使用默认接收邮箱：{email}',
    receiverEmailDescNoDefault: '告警通知的接收邮箱。可在系统设置中配置默认接收邮箱。',
    webhookNotification: '🔗 Webhook通知',
    webhookNotificationDesc: '告警触发时会向此URL发送POST请求，包含告警详情JSON数据',
    enableRule: '启用此规则',
    budgetOverspend: '预算超支',
    resourceAnomaly: '资源异常',
    securityCompliance: '安全合规',
    info: '信息',
    warning: '警告',
    error: '错误',
    critical: '严重',
    totalCost: '总成本',
    dailyCost: '日成本',
    monthlyCost: '月成本',
    greaterThan: '大于',
    greaterThanOrEqual: '大于等于',
    lessThan: '小于',
    lessThanOrEqual: '小于等于',
    notificationChannelsLabel: '通知渠道:',
    noChannelsWarning: '未配置通知渠道，告警将不会发送',
  },
  customDashboards: {
    title: '自定义仪表盘',
    description: '创建和管理自定义仪表盘，灵活配置数据展示',
    noDashboards: '还没有自定义仪表盘',
    noDashboardsDesc: '点击上方"新建仪表盘"按钮创建第一个仪表盘',
    noMatchDashboards: '未找到匹配的仪表盘',
    tryOtherKeywords: '尝试使用其他关键词搜索',
    createDashboard: '新建仪表盘',
    editDashboard: '编辑仪表盘',
    searchPlaceholder: '搜索仪表盘...',
    noWidgets: '暂无组件，点击上方按钮添加',
    deleteFailed: '删除失败',
    saveFailed: '保存失败',
    deleteConfirm: '确定要删除这个仪表盘吗？',
    gridLayout: '网格布局',
    freeLayout: '自由布局',
    widgets: '个组件',
    widgetsUnit: '个组件',
    updatedAt: '更新于',
    createdAt: '创建于',
    view: '查看',
    shared: '已共享',
    dashboardName: '仪表盘名称',
    dashboardDescription: '描述',
    layoutType: '布局类型',
    shareDashboard: '共享仪表盘',
    widgetList: '组件列表',
    addMetric: '+ 指标',
    addChart: '+ 图表',
    addTable: '+ 表格',
    widgetTitle: '组件标题',
    metric: '📊 指标',
    chart: '📈 图表',
    table: '📋 表格',
    cancel: '取消',
    save: '保存',
  },
  virtualTags: {
    title: '虚拟标签管理',
    description: '通过规则引擎创建虚拟标签，用于成本分配和分组，无需修改云资源实际标签',
    noTags: '暂无虚拟标签',
    noTagsDesc: '点击上方"新建标签"按钮创建第一个标签',
    noMatchTags: '未找到匹配的标签',
    tryOtherKeywords: '尝试其他搜索词',
    createTag: '新建标签',
    editTag: '编辑标签',
    searchPlaceholder: '搜索标签名称、key或value...',
    deleteConfirm: '确定要删除这个标签吗？',
    deleteFailed: '删除失败',
    selectAccountFirst: '请先选择账号',
    fillRequiredFields: '请填写所有必填字段',
    atLeastOneRule: '至少需要一个有效的规则',
    saveFailed: '保存失败',
    previewFailed: '预览失败',
    previewMatchingResources: '预览匹配资源',
    ruleCount: '规则数量',
    priority: '优先级',
    moreRules: '更多规则...',
    configureTagRules: '配置标签规则，用于匹配云资源',
    tagName: '标签名称',
    tagKey: '标签Key',
    tagValue: '标签Value',
    priorityDesc: '数字越大优先级越高',
    field: '字段',
    operator: '操作符',
    pattern: '模式',
    matchingRules: '匹配规则',
    addRule: '添加规则',
    rule: '规则',
    exampleProduction: '例如：生产环境',
    exampleEnvironment: '例如：environment',
    exampleProd: '例如：prod',
    resourceName: '资源名称',
    region: '区域',
    resourceType: '资源类型',
    instanceId: '实例ID',
    contains: '包含',
    equals: '等于',
    startsWith: '开头',
    endsWith: '结尾',
    regex: '正则表达式',
    saving: '保存中...',
  },
  costAllocation: {
    title: '成本分配',
    description: '管理成本分配规则和查看分配结果',
    rules: '分配规则',
    results: '分配结果',
    rulesTitle: '成本分配规则',
    rulesDescription: '配置和管理成本分配规则',
    noRules: '暂无成本分配规则',
    noRulesDesc: '创建第一个成本分配规则来分配共享成本',
    noResults: '暂无分配结果',
    noResultsDesc: '执行成本分配规则后，结果将显示在这里',
    createRule: '新建分配规则',
    editRule: '编辑分配规则',
    deleteConfirm: '确定要删除此成本分配规则吗？',
    deleteFailed: '删除失败',
    executeSuccess: '成本分配执行成功',
    executeFailed: '执行失败',
    saveFailed: '保存失败',
    configureRule: '配置成本分配规则',
    ruleName: '规则名称',
    ruleDescription: '描述',
    allocationMethod: '分配方法',
    allocationTarget: '分配目标',
    allocationTargetPlaceholder: '输入目标名称（如：部门、项目等）',
    add: '添加',
    weight: '权重',
    enableRule: '启用此规则',
    enabled: '已启用',
    disabled: '已禁用',
    execute: '执行',
    period: '周期',
    totalCost: '总成本',
    allocated: '已分配',
    unallocated: '未分配',
    allocationRate: '分配率',
    allocationDetails: '分配明细',
    methods: {
      equal: '平均分配',
      proportional: '按比例分配',
      usage_based: '按使用量分配',
      tag_based: '按标签分配',
      custom: '自定义规则',
    },
  },
  dashboardView: {
    saveFailed: '保存失败',
    dashboardNotFound: '仪表盘不存在',
    backToList: '返回列表',
    back: '返回',
    cancel: '取消',
    save: '保存',
    editLayout: '编辑布局',
    editModeHint: '💡 编辑模式：拖拽组件调整位置和大小，完成后点击"保存"',
  },
  cis: {
    title: 'CIS合规检查',
    description: 'CIS Benchmark合规性检查',
    complianceRate: '合规度',
    checks: '检查项',
    noChecks: '暂无检查项',
    loading: '加载中...',
  },
  discountTrend: {
    title: '折扣趋势分析',
    description: '分析折扣趋势和模式',
    trendUp: '上升',
    trendDown: '下降',
    productName: '产品名称',
    totalDiscount: '累计折扣',
    avgDiscountRate: '平均折扣率',
    latestDiscountRate: '最新折扣率',
    discountRateChange: '折扣率变化',
    trend: '趋势',
    instanceId: '实例ID',
    instanceName: '实例名称',
    product: '产品',
    officialPrice: '官网价',
    discountAmount: '折扣金额',
    discountRate: '折扣率',
    payableAmount: '应付金额',
    loadFailed: '加载失败',
    showAllHistory: '显示全部历史数据',
    showRecentMonths: '显示最近{months}个月数据',
    months: '个月',
    loadCache: '加载缓存',
    forceRefresh: '强制刷新',
    timeRange: '时间范围',
    last3Months: '近3个月',
    last6Months: '近6个月',
    last1Year: '近1年',
    allTime: '全部时间',
    customRange: '自定义范围',
    startMonth: '开始月份',
    endMonth: '结束月份',
    apply: '应用',
    analyzing: '正在分析账单数据...',
    possibleReasons: '可能的原因:',
    noBillData: '数据库中暂无该账号的账单数据',
    runCommand: '请先运行账单获取命令：./cl bill fetch --account ydzn --use-db',
    waitSync: '或等待自动账单同步任务完成',
    contactAdmin: '如问题持续，请联系管理员',
    latestDiscountRateTitle: '最新折扣率',
    vsFirstMonth: 'vs 首月',
    avgDiscountRateTitle: '平均折扣率',
    recentMonths: '最近 {count} 个月',
    discountTrendTitle: '折扣趋势',
    range: '范围:',
    cumulativeSavingsTitle: '累计节省',
    tabs: {
      overview: '趋势总览',
      products: '产品分析',
      contracts: '合同分析',
      instances: 'TOP实例',
    },
    discountRateTrend: '折扣率变化趋势',
    discountRateUnit: '折扣率 (%)',
    discountAmountComparison: '折扣金额与官网价对比',
    amountUnit: '金额 (¥)',
    productAnalysis: '产品折扣分析 (TOP 20)',
    contractAnalysis: '合同折扣分析 (TOP 10)',
    topInstances: '高折扣实例 TOP 50（最近一个月）',
    cumulativeSavings: '累计节省',
    avgDiscountRateLabel: '平均折扣率',
    latestDiscountRateLabel: '最新折扣率',
    coverageMonths: '覆盖月份',
    monthsUnit: '个月',
    noData: '暂无折扣趋势数据',
  },
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
    editBudget: '编辑预算',
    newBudget: '新建预算',
    configureBudget: '配置预算信息和告警规则',
    budgetName: '预算名称',
    budgetAmountLabel: '预算金额 (CNY)',
    budgetPeriod: '预算周期',
    budgetType: '预算类型',
    startDate: '开始日期',
    alertRules: '告警规则',
    addAlert: '添加告警',
    enable: '启用',
    noAlertRules: '暂无告警规则',
    noAlertRulesDesc: '暂无告警规则，点击"添加告警"添加',
    cancel: '取消',
    save: '保存',
    spendingTrend: '支出趋势',
    date: '日期:',
    spending: '支出',
    thresholdTriggered: '阈值已触发',
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




