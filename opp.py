# --- 그래프 섹션 (가로 가독성 강화 버전) ---
    st.divider()
    st.subheader("📈 실시간 가격 가이드라인 (우측 정렬)")

    fig = go.Figure()

    # 1. 주가 선
    fig.add_trace(go.Scatter(
        x=data.index[-15:], 
        y=data[TICKER].tail(15), 
        mode='lines+markers', 
        name='현재가',
        line=dict(color='#00FF00', width=2)
    ))

    # 가이드라인 설정 (글씨를 밖으로 빼기 위해 별도의 annotation 사용)
    lines = [
        {"y": sell_loc_usd, "color": "blue", "text": "매도 LOC", "pos": "top"},
        {"y": AVG_PRICE_USD, "color": "white", "text": "내 평단가", "pos": "middle"},
        {"y": buy_loc_usd, "color": "red", "text": "매수 LOC", "pos": "bottom"}
    ]

    for line in lines:
        # 가로 점선 추가
        fig.add_hline(
            y=line["y"], 
            line_dash="dot", 
            line_color=line["color"], 
            line_width=2
        )
        
        # 우측 여백에 글씨 추가 (xref="paper"를 사용하여 차트 바깥쪽 정렬)
        fig.add_annotation(
            x=1.02, # 차트 오른쪽 끝에서 살짝 밖으로 (0~1 범위 밖)
            y=line["y"],
            xref="paper",
            yref="y",
            text=f"<b>{line['text']}<br>${line['y']:.2f}</b>",
            showarrow=False,
            font=dict(size=13, color=line["color"]),
            align="left",
            xanchor="left"
        )

    # 차트 레이아웃 설정
    fig.update_layout(
        template="plotly_dark",
        height=550,
        margin=dict(l=10, r=120, t=50, b=10), # 오른쪽 여백(r)을 120으로 대폭 확대
        xaxis=dict(showgrid=True, gridcolor='gray', tickformat='%m-%d'),
        yaxis=dict(showgrid=True, gridcolor='gray', side="left"), # 기본 축은 왼쪽
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)