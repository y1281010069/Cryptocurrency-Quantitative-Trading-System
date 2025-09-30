from flask import Flask, render_template, request, jsonify
import re
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 配置默认的报告文件路径
DEFAULT_REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'multi_timeframe_reports', 'multi_timeframe_analysis_new.txt')


def parse_report_content(file_path=DEFAULT_REPORT_PATH):
    """解析报告文件内容并返回结构化数据"""
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"警告: 报告文件不存在 - {file_path}")
            # 返回包含错误信息的数据结构，不使用模拟数据
            error_data = {
                'analysisTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'timeframeDimensions': '周线→日线→4小时→1小时→15分钟',
                'totalOpportunities': 0,
                'error': f"报告文件不存在: {file_path}",
                'opportunities': []
            }
            return error_data
        
        # 记录文件修改时间，用于调试
        file_mtime = os.path.getmtime(file_path)
        print(f"读取文件: {file_path}, 最后修改时间: {datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 尝试使用不同的编码读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        report_data = {
            'analysisTime': '',
            'timeframeDimensions': '',
            'totalOpportunities': 0,
            'opportunities': []
        }

        # 尝试使用更宽松的正则表达式解析报告头部
        # 我们不依赖于特定的符号和文本，而是寻找包含时间、维度和机会数量的部分
        time_match = re.search(r'鍒嗘瀽鏃堕棿:?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2})', content)
        if time_match:
            report_data['analysisTime'] = time_match.group(1).strip()
        else:
            report_data['analysisTime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        # 设置默认的时间框架维度
        report_data['timeframeDimensions'] = '周线→日线→4小时→1小时→15分钟'
        
        # 尝试从文件中提取机会数量
        opportunities_match = re.search(r'鍙戠幇鏈轰細:?\s*(\d+)', content)
        if opportunities_match:
            try:
                report_data['totalOpportunities'] = int(opportunities_match.group(1).strip())
            except:
                report_data['totalOpportunities'] = 0

        # 使用更宽松的正则表达式解析每个交易机会
        # 查找以"銆愭満浼?"或"【机会"开始的行
        opportunity_markers = re.finditer(r'(銆愭満浼?|【机会)\s*(\d+)\s*(銆?|】)', content)
        
        for marker_idx, marker in enumerate(opportunity_markers):
            # 获取匹配的所有组
            groups = marker.groups()
            # 提取需要的信息
            opportunity_type = groups[0]  # 銆愭満浼? 或 【机会
            try:
                rank = int(groups[1])  # 排名数字
            except:
                rank = marker_idx + 1
            closing_char = groups[2]  # 銆? 或 】
            
            # 获取当前匹配的结束位置
            end_pos = marker.end()
            
            # 查找下一个机会的开始位置
            next_opportunity_match = re.search(r'(銆愭満浼?|【机会)', content[end_pos:])
            
            # 确定当前机会的文本块范围
            if next_opportunity_match:
                block_end = end_pos + next_opportunity_match.start()
            else:
                block_end = len(content)
            
            # 提取当前机会的文本块
            block_text = content[end_pos:block_end]
            
            # 从文本块中提取交易对
            symbol_match = re.search(r'([A-Z0-9]+/[A-Z0-9]+)', block_text)
            if symbol_match:
                symbol = symbol_match.group(1)
            else:
                symbol = f'未知交易对_{rank}'
            
            # 提取建议动作
            action_match = re.search(r'(缁煎悎寤鸿:?|综合建议:?)\s*([^\n]+)', block_text)
            action = action_match.group(2).strip() if action_match else '未知'
            
            # 提取信心等级
            confidence_match = re.search(r'(淇″績绛夌骇:?|信心等级:?)\s*([^\n]+)', block_text)
            confidence = confidence_match.group(2).strip() if confidence_match else '未知'
            
            # 提取总评分
            score_match = re.search(r'(鎬昏瘎鍒?|总评分:)\s*([\d.]+)', block_text)
            if score_match:
                try:
                    totalScore = float(score_match.group(2).strip())
                except:
                    totalScore = 0.0
            else:
                totalScore = 0.0
            
            # 提取当前价格
            price_match = re.search(r'(褰撳墠浠锋牸:?|当前价格:?)\s*([\d.]+)', block_text)
            if price_match:
                try:
                    currentPriceValue = float(price_match.group(2).strip())
                except:
                    currentPriceValue = 0.0
            else:
                currentPriceValue = 0.0
            
            # 提取多时间框架分析
            weeklyTrend = dailyTrend = h4Signal = h1Signal = m15Signal = '未知'
            timeframes_match = re.finditer(r'(鍛ㄧ嚎瓒嬪娍:?|周线趋势:?)\s*([^\n]+)', block_text)
            for tm in timeframes_match:
                weeklyTrend = tm.group(2).strip()
            
            timeframes_match = re.finditer(r'(鏃ョ嚎瓒嬪娍:?|日线趋势:?)\s*([^\n]+)', block_text)
            for tm in timeframes_match:
                dailyTrend = tm.group(2).strip()
            
            timeframes_match = re.finditer(r'(4灏忔椂淇″彿:?|4小时信号:?)\s*([^\n]+)', block_text)
            for tm in timeframes_match:
                h4Signal = tm.group(2).strip()
            
            timeframes_match = re.finditer(r'(1灏忔椂淇″彿:?|1小时信号:?)\s*([^\n]+)', block_text)
            for tm in timeframes_match:
                h1Signal = tm.group(2).strip()
            
            timeframes_match = re.finditer(r'(15鍒嗛挓淇″彿:?|15分钟信号:?)\s*([^\n]+)', block_text)
            for tm in timeframes_match:
                m15Signal = tm.group(2).strip()
            
            # 提取目标价格
            targetShort = stopLoss = 0.0
            
            # 提取短期目标 (现在是1.5倍ATR)
            target_match = re.search(r'(鐭湡鐩爣|短期目标).*?:?\s*([\d.]+)', block_text)
            if target_match:
                try:
                    targetShort = float(target_match.group(2).strip())
                except:
                    pass
            
            # 提取止损价格 (现在是1倍ATR的反向价格)
            target_match = re.search(r'(姝㈡崯浠锋牸|止损价格).*?:?\s*([\d.]+)', block_text)
            if target_match:
                try:
                    stopLoss = float(target_match.group(2).strip())
                except:
                    pass
            
            # 计算百分比变化
            try:
                shortPct = ((targetShort / currentPriceValue - 1) * 100) if currentPriceValue > 0 else 0.0
                stopPct = ((stopLoss / currentPriceValue - 1) * 100) if currentPriceValue > 0 else 0.0
                mediumPct = longPct = 0.0  # 不再使用中期和长期目标
            except (ValueError, ZeroDivisionError):
                shortPct = stopPct = mediumPct = longPct = 0.0
            
            # 提取分析依据
            reasoning_match = re.search(r'(鍒嗘瀽渚濇嵁:?|分析依据:?)\s*([^\n]+)', block_text)
            reasoning = reasoning_match.group(2).strip() if reasoning_match else '无'
            
            # 添加到机会列表
            report_data['opportunities'].append({
                'rank': rank,
                'symbol': symbol,
                'action': action,
                'confidence': confidence,
                'totalScore': totalScore,
                'currentPrice': currentPriceValue,
                'weeklyTrend': weeklyTrend,
                'dailyTrend': dailyTrend,
                'h4Signal': h4Signal,
                'h1Signal': h1Signal,
                'm15Signal': m15Signal,
                'targetShort': targetShort,
                'stopLoss': stopLoss,
                'reasoning': reasoning,
                'shortPct': round(shortPct, 1),
                'mediumPct': round(mediumPct, 1),
                'longPct': round(longPct, 1),
                'stopPct': round(stopPct, 1)
            })
        
        # 更新实际找到的机会数量
        report_data['totalOpportunities'] = len(report_data['opportunities'])
        
        # 如果没有找到交易机会，返回空列表
        if not report_data['opportunities']:
            report_data['totalOpportunities'] = 0
            
        return report_data
        
    except Exception as e:
        # 详细记录解析错误
        print(f"解析报告文件失败: {e}")
        
        # 尝试使用更宽松的解析方式或者直接返回错误信息
        try:
            # 读取文件内容作为错误信息的一部分
            with open(file_path, 'r', encoding='utf-8') as f:
                content_preview = f.read(500)  # 只读取前500个字符
            print(f"文件内容预览: {content_preview}")
        except Exception as read_error:
            print(f"读取文件内容失败: {read_error}")
            
        # 返回包含错误信息的特殊数据结构
        error_data = {
            'analysisTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timeframeDimensions': '周线→日线→4小时→1小时→15分钟',
            'totalOpportunities': 0,
            'error': str(e),
            'opportunities': []
        }
        
        # 如果出现解析错误，优先返回错误信息而不是模拟数据
        return error_data





@app.route('/')
def index():
    """主页面路由"""
    # 从URL参数获取报告文件路径
    report_path = request.args.get('file', DEFAULT_REPORT_PATH)
    # 解析报告数据
    report_data = parse_report_content(report_path)
    
    # 统计各类机会数量
    buy_count = len([op for op in report_data['opportunities'] if '买入' in op['action']])
    sell_count = len([op for op in report_data['opportunities'] if '卖出' in op['action']])
    watch_count = len([op for op in report_data['opportunities'] if '观望' in op['action']])
    
    # 渲染模板并传递数据
    return render_template('index.html', 
                          report_data=report_data,
                          buy_count=buy_count,
                          sell_count=sell_count,
                          watch_count=watch_count)


@app.route('/api/data')
def api_data():
    """API接口，返回JSON格式的报告数据"""
    report_path = request.args.get('file', DEFAULT_REPORT_PATH)
    report_data = parse_report_content(report_path)
    return jsonify(report_data)


@app.route('/api/filter')
def filter_data():
    """API接口，根据筛选条件返回过滤后的数据"""
    # 获取筛选参数
    filter_type = request.args.get('type', 'all')
    search_term = request.args.get('search', '').lower().strip()
    
    # 解析报告数据
    report_path = request.args.get('file', DEFAULT_REPORT_PATH)
    report_data = parse_report_content(report_path)
    
    # 应用筛选条件
    filtered_opportunities = []
    
    for opportunity in report_data['opportunities']:
        # 应用操作类型筛选
        action_match = (filter_type == 'all' or filter_type in opportunity['action'])
        # 应用搜索筛选
        search_match = (search_term == '' or search_term in opportunity['symbol'].lower())
        
        if action_match and search_match:
            filtered_opportunities.append(opportunity)
    
    # 返回过滤后的数据
    return jsonify({
        'opportunities': filtered_opportunities,
        'total': len(filtered_opportunities)
    })


if __name__ == '__main__':
    # 获取本地IP地址
    import socket
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except:
        local_ip = '127.0.0.1'
    
    # 打印启动信息
    print('=' * 80)
    print('多时间框架分析报告查看器 - Python版')
    print('=' * 80)
    print(f'本地访问地址: http://127.0.0.1:5000')
    print(f'局域网访问地址: http://{local_ip}:5000')
    print('请在浏览器中打开上述地址查看报告')
    print('手机查看请确保与电脑连接同一Wi-Fi网络，然后访问局域网地址')
    print('=' * 80)
    
    # 启动Flask应用（生产环境应使用专业Web服务器）
    app.run(host='0.0.0.0', debug=False)