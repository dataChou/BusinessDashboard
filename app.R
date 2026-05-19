# 安装必要包（如果尚未安装）
if (!require("shiny")) install.packages("shiny")
if (!require("shinydashboard")) install.packages("shinydashboard")
if (!require("dplyr")) install.packages("dplyr")
if (!require("plotly")) install.packages("plotly")
if (!require("readr")) install.packages("readr")
if (!require("DT")) install.packages("DT")
if (!require("shinyWidgets")) install.packages("shinyWidgets")  # 用于美观的多选框

library(shiny)
library(shinydashboard)
library(dplyr)
library(plotly)
library(readr)
library(DT)
library(shinyWidgets)

# ==================== 读取数据 ====================
df_raw <- read_csv("pet_hospital_data.csv", locale = locale(encoding = "UTF-8"))
df_raw$日期 <- as.Date(df_raw$日期)

today <- as.Date("2026-05-19")

# ==================== UI ====================
ui <- dashboardPage(
  dashboardHeader(title = "🐾 宠物医院经营分析看板"),
  
  dashboardSidebar(
    sidebarMenu(
      menuItem("经营概览", tabName = "dashboard", icon = icon("dashboard")),
      menuItem("流失客户", tabName = "lost", icon = icon("exclamation-triangle")),
      menuItem("原始数据", tabName = "raw", icon = icon("table"))
    ),
    # 添加筛选器区域
    hr(),
    h5("全局筛选", style = "padding-left: 15px;"),
    pickerInput(
      inputId = "doctor_filter",
      label = "选择医生",
      choices = unique(df_raw$医生),
      selected = unique(df_raw$医生),
      options = list(`actions-box` = TRUE, `live-search` = TRUE),
      multiple = TRUE
    ),
    pickerInput(
      inputId = "service_filter",
      label = "选择服务项目",
      choices = unique(df_raw$服务项目),
      selected = unique(df_raw$服务项目),
      options = list(`actions-box` = TRUE),
      multiple = TRUE
    ),
    actionButton("reset_filters", "重置筛选", icon = icon("undo"), 
                 style = "margin: 10px 15px; width: calc(100% - 30px);")
  ),
  
  dashboardBody(
    tabItems(
      # ----- 经营概览页面 -----
      tabItem(tabName = "dashboard",
              fluidRow(
                valueBoxOutput("total_customers_box"),
                valueBoxOutput("total_revenue_box"),
                valueBoxOutput("lost_rate_box"),
                valueBoxOutput("avg_ticket_box"),
                valueBoxOutput("total_orders_box")
              ),
              fluidRow(
                box(plotlyOutput("pie_chart"), title = "客户分层占比", width = 6, status = "primary"),
                box(plotlyOutput("service_bar"), title = "服务项目营收", width = 6, status = "success")
              ),
              fluidRow(
                box(plotlyOutput("doctor_bar"), title = "医生接诊量排行", width = 6, status = "info"),
                box(plotlyOutput("price_bar"), title = "服务项目客单价", width = 6, status = "warning")
              ),
              fluidRow(
                box(plotlyOutput("monthly_trend"), title = "月度营收与订单数趋势", width = 12, status = "primary")
              ),
              fluidRow(
                box(DTOutput("lost_table"), title = "流失客户列表（前100）", width = 12, status = "danger")
              )
      ),
      # ----- 流失客户页面（完整列表）-----
      tabItem(tabName = "lost",
              fluidRow(
                box(DTOutput("lost_table_full"), title = "流失客户列表（超过6个月未消费）", width = 12, status = "danger")
              )
      ),
      # ----- 原始数据页面 -----
      tabItem(tabName = "raw",
              fluidRow(
                box(DTOutput("raw_table"), title = "原始消费记录", width = 12, status = "primary")
              )
      )
    )
  )
)

# ==================== Server ====================
server <- function(input, output, session) {
  
  # 重置筛选器
  observeEvent(input$reset_filters, {
    updatePickerInput(session, "doctor_filter", selected = unique(df_raw$医生))
    updatePickerInput(session, "service_filter", selected = unique(df_raw$服务项目))
  })
  
  # 根据筛选条件生成数据子集
  filtered_data <- reactive({
    req(input$doctor_filter, input$service_filter)
    df <- df_raw %>%
      filter(医生 %in% input$doctor_filter,
             服务项目 %in% input$service_filter)
    
    # 若筛选后无数据，返回空数据框并提示
    if (nrow(df) == 0) {
      showNotification("当前筛选条件下无数据，请放宽筛选条件", type = "warning", duration = 5)
      return(NULL)
    }
    df
  })
  
  # 基于筛选数据计算客户RFM
  customer_data <- reactive({
    df <- filtered_data()
    if (is.null(df)) return(NULL)
    
    last_visit <- df %>%
      group_by(宠主ID) %>%
      summarise(最后消费日期 = max(日期), .groups = "drop") %>%
      mutate(R = as.numeric(today - 最后消费日期))
    
    freq <- df %>%
      group_by(宠主ID) %>%
      summarise(F = n(), .groups = "drop")
    
    amount <- df %>%
      group_by(宠主ID) %>%
      summarise(M = sum(消费金额), .groups = "drop")
    
    customer <- last_visit %>%
      left_join(freq, by = "宠主ID") %>%
      left_join(amount, by = "宠主ID") %>%
      left_join(df %>% select(宠主ID, 宠主姓名) %>% distinct(), by = "宠主ID") %>%
      mutate(
        分层 = case_when(
          R <= 30 ~ "高价值客户",
          R <= 90 ~ "活跃客户",
          R <= 180 ~ "沉睡客户",
          TRUE ~ "流失客户"
        )
      )
    customer
  })
  
  # ---------- KPI ----------
  output$total_customers_box <- renderValueBox({
    cust <- customer_data()
    if (is.null(cust)) {
      valueBox("0人", "总客户数", icon = icon("paw"), color = "blue")
    } else {
      valueBox(paste0(nrow(cust), "人"), "总客户数", icon = icon("paw"), color = "blue")
    }
  })
  
  output$total_revenue_box <- renderValueBox({
    df <- filtered_data()
    if (is.null(df)) {
      valueBox("0万", "总营收", icon = icon("yen-sign"), color = "green")
    } else {
      rev_wan <- sum(df$消费金额) / 10000
      valueBox(paste0(round(rev_wan, 1), "万"), "总营收", icon = icon("yen-sign"), color = "green")
    }
  })
  
  output$lost_rate_box <- renderValueBox({
    cust <- customer_data()
    if (is.null(cust)) {
      valueBox("0%", "流失率", icon = icon("exclamation-triangle"), color = "red")
    } else {
      lost <- sum(cust$R > 180)
      rate <- round(lost / nrow(cust) * 100, 1)
      valueBox(paste0(rate, "%"), "流失率", icon = icon("exclamation-triangle"), color = "red")
    }
  })
  
  output$avg_ticket_box <- renderValueBox({
    df <- filtered_data()
    if (is.null(df) || nrow(df) == 0) {
      valueBox("0元", "整体客单价", icon = icon("credit-card"), color = "yellow")
    } else {
      avg <- round(sum(df$消费金额) / nrow(df), 0)
      valueBox(paste0(avg, "元"), "整体客单价", icon = icon("credit-card"), color = "yellow")
    }
  })
  
  output$total_orders_box <- renderValueBox({
    df <- filtered_data()
    if (is.null(df)) {
      valueBox("0笔", "总订单数", icon = icon("clipboard-list"), color = "purple")
    } else {
      valueBox(paste0(nrow(df), "笔"), "总订单数", icon = icon("clipboard-list"), color = "purple")
    }
  })
  
  # ---------- 客户分层饼图 ----------
  output$pie_chart <- renderPlotly({
    cust <- customer_data()
    if (is.null(cust)) return(plotly_empty(type = "pie", title = "无数据"))
    
    layer_counts <- cust %>%
      count(分层) %>%
      mutate(分层 = factor(分层, levels = c("高价值客户", "活跃客户", "沉睡客户", "流失客户")))
    
    plot_ly(layer_counts, labels = ~分层, values = ~n, type = 'pie',
            textposition = 'inside', textinfo = 'percent+label',
            marker = list(colors = c('#2ECC71', '#3498DB', '#F39C12', '#E74C3C'))) %>%
      layout(title = "")
  })
  
  # ---------- 服务项目营收柱状图 ----------
  output$service_bar <- renderPlotly({
    df <- filtered_data()
    if (is.null(df)) return(plotly_empty(type = "bar", title = "无数据"))
    
    service_stats <- df %>%
      group_by(服务项目) %>%
      summarise(总金额 = sum(消费金额), .groups = "drop") %>%
      arrange(desc(总金额))
    
    plot_ly(service_stats, x = ~服务项目, y = ~总金额, type = 'bar',
            marker = list(color = c('#1ABC9C', '#2ECC71', '#3498DB', '#9B59B6', '#E74C3C'))) %>%
      layout(title = "", xaxis = list(title = ""), yaxis = list(title = "营收（元）"))
  })
  
  # ---------- 医生接诊量柱状图 ----------
  output$doctor_bar <- renderPlotly({
    df <- filtered_data()
    if (is.null(df)) return(plotly_empty(type = "bar", title = "无数据"))
    
    doctor_stats <- df %>%
      group_by(医生) %>%
      summarise(接诊量 = n(), .groups = "drop") %>%
      arrange(desc(接诊量))
    
    plot_ly(doctor_stats, x = ~医生, y = ~接诊量, type = 'bar',
            marker = list(color = '#3498DB')) %>%
      layout(title = "", xaxis = list(title = ""), yaxis = list(title = "接诊量（次）"))
  })
  
  # ---------- 服务项目客单价水平条形图 ----------
  output$price_bar <- renderPlotly({
    df <- filtered_data()
    if (is.null(df)) return(plotly_empty(type = "bar", title = "无数据"))
    
    item_price <- df %>%
      group_by(服务项目) %>%
      summarise(客单价 = mean(消费金额), .groups = "drop") %>%
      arrange(客单价)
    
    plot_ly(item_price, y = ~服务项目, x = ~客单价, type = 'bar', orientation = 'h',
            marker = list(color = ~客单价, colorscale = 'Viridis', showscale = FALSE)) %>%
      layout(title = "", xaxis = list(title = "客单价（元）"), yaxis = list(title = ""))
  })
  
  # ---------- 月度趋势（折线+柱状）----------
  output$monthly_trend <- renderPlotly({
    df <- filtered_data()
    if (is.null(df)) return(plotly_empty(type = "scatter", title = "无数据"))
    
    df$月份 <- format(df$日期, "%Y-%m")
    monthly <- df %>%
      group_by(月份) %>%
      summarise(营收 = sum(消费金额), 订单数 = n(), .groups = "drop")
    
    plot_ly() %>%
      add_trace(x = ~monthly$月份, y = ~monthly$营收, type = 'scatter', mode = 'lines+markers',
                name = '营收', line = list(color = '#2ECC71', width = 3),
                marker = list(size = 8)) %>%
      add_trace(x = ~monthly$月份, y = ~monthly$订单数, type = 'bar', name = '订单数',
                marker = list(color = '#3498DB', opacity = 0.6), yaxis = 'y2') %>%
      layout(
        title = "",
        xaxis = list(title = "月份", tickangle = -45),
        yaxis = list(title = "营收（元）", side = "left"),
        yaxis2 = list(title = "订单数（笔）", overlaying = 'y', side = 'right'),
        hovermode = 'x unified'
      )
  })
  
  # ---------- 流失客户列表（概览页前100）----------
  output$lost_table <- renderDT({
    cust <- customer_data()
    if (is.null(cust)) return(datatable(data.frame(提示 = "无数据")))
    
    lost_data <- cust %>%
      filter(R > 180) %>%
      select(宠主ID, 宠主姓名, 最后消费日期, M, F, R) %>%
      arrange(desc(R)) %>%
      head(100)
    
    colnames(lost_data) <- c("宠主ID", "宠主姓名", "最近消费日期", "总消费金额", "总消费次数", "未登录天数")
    datatable(lost_data, options = list(pageLength = 10, scrollX = TRUE), rownames = FALSE)
  })
  
  # ---------- 流失客户列表（独立页面完整列表）----------
  output$lost_table_full <- renderDT({
    cust <- customer_data()
    if (is.null(cust)) return(datatable(data.frame(提示 = "无数据")))
    
    lost_data <- cust %>%
      filter(R > 180) %>%
      select(宠主ID, 宠主姓名, 最后消费日期, M, F, R) %>%
      arrange(desc(R))
    
    colnames(lost_data) <- c("宠主ID", "宠主姓名", "最近消费日期", "总消费金额", "总消费次数", "未登录天数")
    datatable(lost_data, options = list(pageLength = 25, scrollX = TRUE), rownames = FALSE)
  })
  
  # ---------- 原始数据表 ----------
  output$raw_table <- renderDT({
    df <- filtered_data()
    if (is.null(df)) return(datatable(data.frame(提示 = "无数据")))
    
    df_display <- df %>%
      select(日期, 宠主ID, 宠主姓名, 宠物类型, 服务项目, 消费金额, 医生, 客户来源)
    datatable(df_display, options = list(pageLength = 25, scrollX = TRUE), rownames = FALSE)
  })
}

# 运行应用
shinyApp(ui = ui, server = server)