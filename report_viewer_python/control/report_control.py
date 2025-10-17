import os
import re
from datetime import datetime

class ReportControl:
    def __init__(self, default_report_path=None):
        # 如果没有提供默认路径，使用标准路径
        if default_report_path is None:
            self.default_report_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'reports', 
                'multi_timeframe_analysis_new.txt'
            )
        else:
            self.default_report_path = default_report_path
    
    def parse_report_content(self, file_path=None):
        """解析报告文件内容并返回结构化数据"""
        # 使用指定路径或默认路径
        report_path = file_path or self.default_report_path
        
        try:
            # 检查文件是否存在
            if not os.path.exists(report_path):
                print(f"警告: 报告文件不存在 - {report_path}")
                # 返回包含错误信息的数据结构，不使用模拟数据
                error_data = {
                    'analysisTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'timeframeDimensions': '周线→日线→4小时→1小时→15分钟',
                    'totalOpportunities': 0,
                    'error': f"报告文件不存在: {report_path}",
                    'opportunities': []
                }
                return error_data
            
            # 记录文件修改时间，用于调试
            file_mtime = os.path.getmtime(report_path)
            print(f"读取文件: {report_path}, 最后修改时间: {datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 尝试使用不同的编码读取文件内容
            content = self._read_file_with_encoding(report_path)
            
            report_data = {
                'analysisTime': '',
                'timeframeDimensions': '',
                'totalOpportunities': 0,
                'opportunities': []
            }

            # 解析报告头部信息
            # 使用正确的中文文本，而不是乱码
            time_match = re.search(r'分析时间:?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2})', content)
            if time_match:
                report_data['analysisTime'] = time_match.group(1).strip()
            else:
                report_data['analysisTime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
            # 解析时间框架维度
            dimension_match = re.search(r'时间框架维度:?\s*(.+)', content)
            if dimension_match:
                report_data['timeframeDimensions'] = dimension_match.group(1).strip()
            else:
                report_data['timeframeDimensions'] = '周线→日线→4小时→1小时→15分钟'
            
            # 解析发现的机会数量
            opportunities_match = re.search(r'发现机会:?\s*(\d+)', content)
            if opportunities_match:
                report_data['totalOpportunities'] = int(opportunities_match.group(1))
            else:
                # 如果无法从头部解析，我们将在解析完所有机会后更新这个值
                report_data['totalOpportunities'] = 0
            
            # 解析交易机会数据
            # 匹配每个机会的完整块
            opportunity_blocks = re.findall(r'【机会 \d+】(.*?)(?=\n【机会 \d+】|\Z)', content, re.DOTALL)
            
            for block in opportunity_blocks:
                opportunity = {
                    'symbol': '',
                    'action': '',
                    'confidence': '',
                    'totalScore': 0,
                    'currentPrice': 0,
                    'weeklySignal': '',
                    'dailySignal': '',
                    'h4Signal': '',
                    'h1Signal': '',
                    'm15Signal': '',
                    'targetPrice': 0,
                    'stopLossPrice': 0,
                    'shortPct': 0,  # 添加短目标百分比
                    'stopPct': 0,   # 添加止损百分比
                    'analysisReason': ''
                }
                
                # 提取交易对
                symbol_match = re.search(r'交易对[:：]\s*(\w+/\w+)', block)
                if symbol_match:
                    opportunity['symbol'] = symbol_match.group(1)
                
                # 提取综合建议（买入/卖出/观望）
                action_match = re.search(r'综合建议[:：]\s*(买入|卖出|观望)', block)
                if action_match:
                    opportunity['action'] = action_match.group(1)
                
                # 提取信心等级
                confidence_match = re.search(r'信心等级[:：]\s*(高|中|低)', block)
                if confidence_match:
                    opportunity['confidence'] = confidence_match.group(1)
                
                # 提取总评分
                score_match = re.search(r'总评分[:：]\s*([-\d.]+)', block)
                if score_match:
                    opportunity['totalScore'] = float(score_match.group(1))
                
                # 提取当前价格
                price_match = re.search(r'当前价格[:：]\s*([\d.]+)', block)
                if price_match:
                    opportunity['currentPrice'] = float(price_match.group(1))
                
                # 提取各时间框架信号
                weekly_match = re.search(r'周线趋势[:：]\s*(买入|卖出|观望)', block)
                if weekly_match:
                    opportunity['weeklySignal'] = weekly_match.group(1)
                
                daily_match = re.search(r'日线趋势[:：]\s*(买入|卖出|观望)', block)
                if daily_match:
                    opportunity['dailySignal'] = daily_match.group(1)
                
                h4_match = re.search(r'4小时信号[:：]\s*(买入|卖出|观望|强烈买入|强烈卖出)', block)
                if h4_match:
                    opportunity['h4Signal'] = h4_match.group(1)
                
                h1_match = re.search(r'1小时信号[:：]\s*(买入|卖出|观望|强烈买入|强烈卖出)', block)
                if h1_match:
                    opportunity['h1Signal'] = h1_match.group(1)
                
                m15_match = re.search(r'15分钟信号[:：]\s*(买入|卖出|观望|强烈买入|强烈卖出)', block)
                if m15_match:
                    opportunity['m15Signal'] = m15_match.group(1)
                
                # 提取短期目标
                target_match = re.search(r'短期目标[:：]\s*([\d.]+)', block)
                if target_match:
                    opportunity['targetPrice'] = float(target_match.group(1))
                
                # 提取止损价格
                stop_loss_match = re.search(r'止损价格[:：]\s*([\d.]+)', block)
                if stop_loss_match:
                    opportunity['stopLossPrice'] = float(stop_loss_match.group(1))
                    
                # 计算短目标百分比和止损百分比
                if opportunity['currentPrice'] > 0:
                    # 短目标百分比 (目标价格相对于当前价格的百分比)
                    if opportunity['targetPrice'] > 0:
                        opportunity['shortPct'] = round((opportunity['targetPrice'] - opportunity['currentPrice']) / opportunity['currentPrice'] * 100, 2)
                    
                    # 止损百分比 (止损价格相对于当前价格的百分比)
                    if opportunity['stopLossPrice'] > 0:
                        opportunity['stopPct'] = round((opportunity['stopLossPrice'] - opportunity['currentPrice']) / opportunity['currentPrice'] * 100, 2)
                
                # 提取分析依据
                reason_match = re.search(r'分析依据[:：]\s*(.+)', block)
                if reason_match:
                    opportunity['analysisReason'] = reason_match.group(1).strip()
                
                # 只有当至少有交易对和操作建议时，才将该机会添加到列表中
                if opportunity['symbol'] and opportunity['action']:
                    report_data['opportunities'].append(opportunity)
            
            # 更新机会总数
            report_data['totalOpportunities'] = len(report_data['opportunities'])
            print(f"成功解析了{report_data['totalOpportunities']}个交易机会")
            
            return report_data
            
        except Exception as e:
            print(f"解析报告文件时发生错误: {e}")
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            
            # 返回错误数据
            error_data = {
                'analysisTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'timeframeDimensions': '周线→日线→4小时→1小时→15分钟',
                'totalOpportunities': 0,
                'error': f"解析报告时发生错误: {str(e)}",
                'opportunities': []
            }
            return error_data
    
    def filter_opportunities(self, file_path=None, filter_type='all', search_term=''):
        """根据筛选条件过滤交易机会数据"""
        # 解析报告数据
        report_data = self.parse_report_content(file_path)
        
        # 应用筛选条件
        filtered_opportunities = []
        search_term = search_term.lower().strip()
        
        for opportunity in report_data['opportunities']:
            # 应用操作类型筛选
            action_match = (filter_type == 'all' or filter_type in opportunity.get('action', ''))
            # 应用搜索筛选
            search_match = (search_term == '' or search_term in opportunity.get('symbol', '').lower())
            
            if action_match and search_match:
                filtered_opportunities.append(opportunity)
        
        return {
            'opportunities': filtered_opportunities,
            'total': len(filtered_opportunities)
        }
    
    def _read_file_with_encoding(self, file_path):
        """尝试使用不同的编码读取文件"""
        encodings = ['utf-8', 'gbk', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，返回空字符串
        print(f"警告: 无法使用任何支持的编码读取文件 - {file_path}")
        return ""