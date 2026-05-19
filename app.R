# 安装必要包（如果还没安装）
if (!require("shinydashboard")) install.packages("shinydashboard")
if (!require("shiny")) install.packages("shiny")
if (!require("ggplot2")) install.packages("ggplot2")
if (!require("dplyr")) install.packages("dplyr")
if (!require("plotly")) install.packages("plotly")
if (!require("readr")) install.packages("readr")
if (!require("DT")) install.packages("DT")

library(shiny)
library(shinydashboard)
library(ggplot2)
library(dplyr)
library(plotly)
library(readr)
library(DT)

# 读取数据
df <- read_csv("pet_hospital_data.csv", locale = locale(encoding = "UTF-8"))
df$日期 <- as.Date(df$日期)

today <- as.Date("2026-05-19")

# 计算RFM
customer_data <- df %>%
  group_by(宠主ID) %>%
  summarise(
    宠主姓名 = first(宠主姓名),
    最后消费日期 = max(日期),
    R = as.numeric(today - 最后消费日期),
    F = n(),
    M = sum(消费金额)
  ) %>%
  mutate(
    分层 = case_when(
      R <= 30 ~ "高价值客户",
      R <= 90 ~ "活跃客户",
      R <= 180 ~ "沉睡客户",
      TRUE ~ "流失客户"
    )
  )

total_customers <- nrow(customer_data)
total_revenue <- sum(df$消费金额)
total_orders <- nrow(df)
lost_customers <- sum(customer_data$R > 180)
lost_rate <- lost_customers / total_customers
avg_ticket <- total_revenue / total_orders

# UI
ui <- dashboardPage(
  dashboardHeader(title = "🐾 宠物医院经营分析看板"),
  
  dashboardSidebar(
    sidebarMenu(
      menuItem("经营概览", tabName = "dashboard", icon = icon("dashboard")),
      menuItem("流失客户", tabName = "lost", icon = icon("exclamation-triangle")),
      menuItem("原始数据", tabName = "raw", icon = icon("table"))
    )
  ),
  
  dashboardBody(
    tabItems(
      # 主看板
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
              )
      ),
      
      # 流失客户页面
      tabItem(tabName = "lost",
              fluidRow(
                box(DTOutput("lost_table"), title = "流失客户列表（超过6个月未消费）", width = 12, status = "danger")
              )
      ),
      
      # 原始数据页面
      tabItem(tabName = "raw",
              fluidRow(
                box(DTOutput("raw_table"), title = "原始消费记录", width = 12, status = "primary")
              )
      )
    )
  )
)

# Server
server <- function(input, output) {
  
  output$total_customers_box <- renderValueBox({
    valueBox(
      value = paste0(total_customers, "人"),
      subtitle = "总客户数",
      icon = icon("paw"),
      color = "blue"
    )
  })
  
  output$total_revenue_box <- renderValueBox({
    valueBox(
      value = paste0(round(total_revenue/10000, 1), "万"),
      subtitle = "总营收",
      icon = icon("yen-sign"),
      color = "green"
    )
  })
  
  output$lost_rate_box <- renderValueBox({
    valueBox(
      value = paste0(round(lost_rate*100, 1), "%"),
      subtitle = "流失率",
      icon = icon("exclamation-triangle"),
      color = "red"
    )
  })
  
  output$avg_ticket_box <- renderValueBox({
    valueBox(
      value = paste0(round(avg_ticket, 0), "元"),
      subtitle = "整体客单价",
      icon = icon("credit-card"),
      color = "yellow"
    )
  })
  
  output$total_orders_box <- renderValueBox({
    valueBox(
      value = paste0(total_orders, "笔"),
      subtitle = "总订单数",
      icon = icon("clipboard-list"),
      color = "purple"
    )
  })
  
  output$pie_chart <- renderPlotly({
    layer_counts <- customer_data %>% count(分层)
    plot_ly(layer_counts, labels = ~分层, values = ~n, type = 'pie',
            textposition = 'inside', textinfo = 'percent+label',
            marker = list(colors = c('#2ECC71', '#3498DB', '#F39C12', '#E74C3C'))) %>%
      layout(title = "")
  })
  
  output$service_bar <- renderPlotly({
    service_stats <- df %>% 
      group_by(服务项目) %>% 
      summarise(总金额 = sum(消费金额)) %>%
      arrange(desc(总金额))
    plot_ly(service_stats, x = ~服务项目, y = ~总金额, type = 'bar',
            marker = list(color = c('#1ABC9C', '#2ECC71', '#3498DB', '#9B59B6', '#E74C3C'))) %>%
      layout(title = "", xaxis = list(title = ""), yaxis = list(title = "营收（元）"))
  })
  
  output$doctor_bar <- renderPlotly({
    doctor_stats <- df %>% 
      group_by(医生) %>% 
      summarise(接诊量 = n()) %>%
      arrange(desc(接诊量))
    plot_ly(doctor_stats, x = ~医生, y = ~接诊量, type = 'bar',
            marker = list(color = '#3498DB')) %>%
      layout(title = "", xaxis = list(title = ""), yaxis = list(title = "接诊量（次）"))
  })
  
  output$price_bar <- renderPlotly({
    item_price <- df %>% 
      group_by(服务项目) %>% 
      summarise(客单价 = mean(消费金额)) %>%
      arrange(客单价)
    plot_ly(item_price, y = ~服务项目, x = ~客单价, type = 'bar', orientation = 'h',
            marker = list(color = ~客单价, colorscale = 'Viridis')) %>%
      layout(title = "", xaxis = list(title = "客单价（元）"), yaxis = list(title = ""))
  })
  
  output$lost_table <- renderDT({
    lost_data <- customer_data %>%
      filter(R > 180) %>%
      select(宠主ID, 宠主姓名, 最后消费日期, 最近消费金额 = M, 总消费次数 = F, 未登录天数 = R) %>%
      arrange(desc(未登录天数))
    
    datatable(lost_data, 
              options = list(pageLength = 20, scrollX = TRUE, dom = 'Bfrtip'),
              rownames = FALSE) %>%
      formatCurrency(columns = "最近消费金额", currency = "¥", interval = 3, mark = ",")
  })
  
  output$monthly_trend <- renderPlotly({
    df$月份 <- format(df$日期, "%Y-%m")
    monthly <- df %>% 
      group_by(月份) %>% 
      summarise(营收 = sum(消费金额), 订单数 = n())
    
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
  
  output$raw_table <- renderDT({
    datatable(df %>% select(日期, 宠主ID, 宠主姓名, 宠物类型, 服务项目, 消费金额, 医生, 客户来源),
              options = list(pageLength = 20, scrollX = TRUE),
              rownames = FALSE)
  })
}

# 运行
shinyApp(ui = ui, server = server)