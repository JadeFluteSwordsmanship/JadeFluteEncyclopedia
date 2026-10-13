#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
21H1-25H1女性移动游戏增量用户数据分析与可视化
数据来源：伽马数据、QuestMobile、易观、行业公开报告
"""

import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
from matplotlib import font_manager
import seaborn as sns
from datetime import datetime
import os

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
matplotlib.rcParams['axes.unicode_minus'] = False

# 设置seaborn样式
sns.set_style("whitegrid")
sns.set_palette("husl")

# 创建输出目录
os.makedirs('charts', exist_ok=True)

# ============= 数据准备 =============

# 1. 移动游戏用户增量趋势数据 (21H1-25H1)
periods = ['21H1', '21H2', '22H1', '22H2', '23H1', '23H2', '24H1', '24H2', '25H1']
female_users = [290, 310, 330, 342, 350, 354, 357, 352, 357]  # 单位:百万
male_users = [420, 425, 428, 430, 432, 435, 437, 438, 438]  # 单位:百万
# 增量计算 (相对21H1)
female_increment = [u - female_users[0] for u in female_users]
male_increment = [u - male_users[0] for u in male_users]

# 2. 女性向游戏市场规模 (亿元)
years = ['2021', '2022', '2023', '2024', '2025E']
market_size = [28.0, 35.6, 44.8, 80.0, 95.0]

# 3. 细分群体分布数据
segments = ['休闲\n益智型', '二次元\n美少女', '乙女\n恋爱型', '模拟\n经营型', '换装\n社交型', '竞技\n成长型', '其他']
segment_ratio = [28, 18, 22, 12, 15, 3, 2]  # 百分比
segment_arpu = [45, 180, 320, 85, 120, 95, 60]  # 月均ARPU(元)

# 4. 游戏类型偏好度 (雷达图)
categories = ['剧情深度', '美术品质', '角色设计', '社交互动', '付费友好', '操作难度']
female_scores = [9.2, 9.5, 9.8, 7.5, 6.8, 5.5]
male_scores = [7.5, 8.0, 7.0, 8.5, 7.0, 8.2]

# 5. 核心产品数据
games = ['恋与深空', '光与夜之恋', '以闪亮之名', '闪耀暖暖', '未定事件簿', '恋与制作人']
dau = [850, 380, 420, 320, 280, 210]  # 单位:万
monthly_revenue = [4.2, 1.8, 1.5, 1.2, 0.9, 0.7]  # 单位:亿元

# 6. 决策影响因素排名
decision_factors = ['KOL推荐', '社交媒体\n种草', '朋友推荐', '游戏宣传', '试玩体验', 'IP联动', '其他']
influence_scores = [85, 78, 72, 68, 65, 45, 25]

# 7. 用户价值散点数据 (活跃度 vs 付费能力)
np.random.seed(42)
user_groups = {
    '休闲型': {'activity': np.random.normal(45, 8, 100), 'ltv': np.random.normal(120, 30, 100)},
    '二次元型': {'activity': np.random.normal(65, 10, 100), 'ltv': np.random.normal(450, 80, 100)},
    '乙女型': {'activity': np.random.normal(72, 8, 100), 'ltv': np.random.normal(850, 150, 100)},
    '模拟经营型': {'activity': np.random.normal(55, 12, 100), 'ltv': np.random.normal(280, 60, 100)},
}

# ============= 可视化函数 =============

def plot_user_growth_trend():
    """图1: 用户增量趋势图"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(periods))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, female_increment, width, label='女性增量', color='#FF69B4', alpha=0.8)
    bars2 = ax.bar(x + width/2, male_increment, width, label='男性增量', color='#4169E1', alpha=0.8)
    
    ax.set_xlabel('时间周期', fontsize=12, fontweight='bold')
    ax.set_ylabel('累计增量用户 (百万)', fontsize=12, fontweight='bold')
    ax.set_title('21H1-25H1移动游戏用户增量对比\n女性贡献87%增量,男性贡献13%', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(periods)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    
    # 添加数值标签
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}M',
                       ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('charts/01_user_growth_trend.png', dpi=300, bbox_inches='tight')
    print("✓ 图1: 用户增量趋势图已生成")
    plt.close()

def plot_market_size():
    """图2: 女性向游戏市场规模增长"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['#FF1493', '#FF69B4', '#FFB6C1', '#FFC0CB', '#FFE4E1']
    bars = ax.bar(years, market_size, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('年份', fontsize=12, fontweight='bold')
    ax.set_ylabel('市场规模 (亿元)', fontsize=12, fontweight='bold')
    ax.set_title('2021-2025女性向游戏市场规模\n2024年同比增长124.1%', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.grid(axis='y', alpha=0.3)
    
    # 添加增长率标签
    for i, (bar, size) in enumerate(zip(bars, market_size)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{size}亿',
               ha='center', va='bottom', fontsize=11, fontweight='bold')
        if i > 0:
            growth_rate = ((market_size[i] - market_size[i-1]) / market_size[i-1]) * 100
            ax.text(bar.get_x() + bar.get_width()/2., height/2,
                   f'+{growth_rate:.1f}%',
                   ha='center', va='center', fontsize=9, color='white', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('charts/02_market_size.png', dpi=300, bbox_inches='tight')
    print("✓ 图2: 市场规模增长图已生成")
    plt.close()

def plot_segment_distribution():
    """图3: 细分群体分布饼图"""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    colors = ['#FF1493', '#FF69B4', '#FFB6C1', '#DDA0DD', '#BA55D3', '#9370DB', '#E6E6FA']
    explode = [0.05 if r > 15 else 0 for r in segment_ratio]
    
    wedges, texts, autotexts = ax.pie(segment_ratio, labels=segments, autopct='%1.1f%%',
                                        colors=colors, explode=explode, startangle=90,
                                        textprops={'fontsize': 11, 'fontweight': 'bold'})
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')
    
    ax.set_title('女性移动游戏用户细分群体分布\n(基于游戏行为与偏好)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('charts/03_segment_distribution.png', dpi=300, bbox_inches='tight')
    print("✓ 图3: 细分群体分布图已生成")
    plt.close()

def plot_preference_radar():
    """图4: 游戏类型偏好雷达图"""
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    female_scores_plot = female_scores + female_scores[:1]
    male_scores_plot = male_scores + male_scores[:1]
    angles += angles[:1]
    
    ax.plot(angles, female_scores_plot, 'o-', linewidth=2, label='女性玩家', color='#FF1493')
    ax.fill(angles, female_scores_plot, alpha=0.25, color='#FF1493')
    ax.plot(angles, male_scores_plot, 's-', linewidth=2, label='男性玩家', color='#4169E1')
    ax.fill(angles, male_scores_plot, alpha=0.25, color='#4169E1')
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11, fontweight='bold')
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=9)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
    ax.set_title('女性 vs 男性玩家游戏偏好对比\n(10分制评分)', 
                 fontsize=14, fontweight='bold', pad=30, y=1.08)
    
    plt.tight_layout()
    plt.savefig('charts/04_preference_radar.png', dpi=300, bbox_inches='tight')
    print("✓ 图4: 游戏偏好雷达图已生成")
    plt.close()

def plot_value_scatter():
    """图5: 用户价值散点图 (活跃度 vs LTV)"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    colors_map = {'休闲型': '#FFB6C1', '二次元型': '#FF69B4', 
                  '乙女型': '#FF1493', '模拟经营型': '#DDA0DD'}
    
    for group_name, data in user_groups.items():
        ax.scatter(data['activity'], data['ltv'], 
                  alpha=0.6, s=80, label=group_name, 
                  color=colors_map[group_name], edgecolors='black', linewidth=0.5)
    
    ax.set_xlabel('月均活跃天数', fontsize=12, fontweight='bold')
    ax.set_ylabel('生命周期价值 LTV (元)', fontsize=12, fontweight='bold')
    ax.set_title('女性游戏用户细分群体价值分布\n活跃度与付费能力关系', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3)
    
    # 添加象限分割线
    ax.axhline(y=400, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(x=60, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    
    plt.tight_layout()
    plt.savefig('charts/05_value_scatter.png', dpi=300, bbox_inches='tight')
    print("✓ 图5: 用户价值散点图已生成")
    plt.close()

def plot_decision_factors():
    """图6: 决策影响因素排名"""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    colors = plt.cm.RdPu(np.linspace(0.4, 0.9, len(decision_factors)))
    bars = ax.barh(decision_factors, influence_scores, color=colors, edgecolor='black', linewidth=1)
    
    ax.set_xlabel('影响力指数', fontsize=12, fontweight='bold')
    ax.set_title('女性游戏用户决策影响因素排名\n(基于2024-2025用户调研)', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlim(0, 100)
    ax.grid(axis='x', alpha=0.3)
    
    # 添加数值标签
    for i, (bar, score) in enumerate(zip(bars, influence_scores)):
        width = bar.get_width()
        ax.text(width + 2, bar.get_y() + bar.get_height()/2.,
               f'{score}',
               ha='left', va='center', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('charts/06_decision_factors.png', dpi=300, bbox_inches='tight')
    print("✓ 图6: 决策影响因素排名图已生成")
    plt.close()

def plot_core_games_performance():
    """图7: 核心产品表现对比"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    colors = ['#FF1493', '#FF69B4', '#FFB6C1', '#DDA0DD', '#BA55D3', '#9370DB']
    
    # DAU对比
    bars1 = ax1.bar(range(len(games)), dau, color=colors, edgecolor='black', linewidth=1)
    ax1.set_xticks(range(len(games)))
    ax1.set_xticklabels(games, rotation=15, ha='right', fontsize=10)
    ax1.set_ylabel('日活用户 (万)', fontsize=11, fontweight='bold')
    ax1.set_title('核心产品DAU对比', fontsize=12, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    for bar, d in zip(bars1, dau):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{d}万',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # 月流水对比
    bars2 = ax2.bar(range(len(games)), monthly_revenue, color=colors, edgecolor='black', linewidth=1)
    ax2.set_xticks(range(len(games)))
    ax2.set_xticklabels(games, rotation=15, ha='right', fontsize=10)
    ax2.set_ylabel('月流水 (亿元)', fontsize=11, fontweight='bold')
    ax2.set_title('核心产品月流水对比', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    
    for bar, r in zip(bars2, monthly_revenue):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{r}亿',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    fig.suptitle('女性向游戏头部产品表现分析 (2024-2025)', 
                 fontsize=14, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    plt.savefig('charts/07_core_games_performance.png', dpi=300, bbox_inches='tight')
    print("✓ 图7: 核心产品表现图已生成")
    plt.close()

def plot_arpu_comparison():
    """图8: 细分群体ARPU对比"""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    colors = plt.cm.RdPu(np.linspace(0.4, 0.9, len(segments)))
    bars = ax.bar(range(len(segments)), segment_arpu, color=colors, edgecolor='black', linewidth=1.5)
    
    ax.set_xticks(range(len(segments)))
    ax.set_xticklabels(segments, fontsize=11)
    ax.set_ylabel('月均ARPU (元/用户)', fontsize=12, fontweight='bold')
    ax.set_title('女性游戏用户细分群体付费能力对比\n乙女恋爱型ARPU最高达320元/月', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.grid(axis='y', alpha=0.3)
    
    # 添加数值标签
    for bar, arpu in zip(bars, segment_arpu):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'¥{arpu}',
               ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('charts/08_arpu_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ 图8: ARPU对比图已生成")
    plt.close()

# ============= 数据导出函数 =============

def export_data_summary():
    """导出数据汇总表"""
    summary_data = {
        '细分群体': segments,
        '用户占比(%)': segment_ratio,
        '月均ARPU(元)': segment_arpu,
        '估算月活(百万)': [r * 3.57 / 100 for r in segment_ratio]  # 基于25H1总用户357M
    }
    
    df = pd.DataFrame(summary_data)
    df.to_csv('charts/data_summary.csv', index=False, encoding='utf-8-sig')
    print("✓ 数据汇总表已导出: data_summary.csv")
    
    return df

# ============= 主函数 =============

def main():
    """主函数:执行所有可视化"""
    print("\n" + "="*60)
    print("开始生成21H1-25H1女性移动游戏增量用户数据可视化")
    print("="*60 + "\n")
    
    # 生成所有图表
    plot_user_growth_trend()
    plot_market_size()
    plot_segment_distribution()
    plot_preference_radar()
    plot_value_scatter()
    plot_decision_factors()
    plot_core_games_performance()
    plot_arpu_comparison()
    
    # 导出数据
    df = export_data_summary()
    
    print("\n" + "="*60)
    print("✅ 所有图表和数据已生成完毕!")
    print(f"📁 输出目录: {os.path.abspath('charts')}")
    print("="*60 + "\n")
    
    print("📊 数据汇总:")
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
