import streamlit as st
from docxtpl import DocxTemplate
from datetime import datetime
import io
import pandas as pd

# [함수] 숫자를 한글 금액으로 변환
def format_ko_money(num):
    try:
        if not num or num == 0: return "영원"
        units = ["", "십", "백", "천"]
        big_units = ["", "만", "억", "조"]
        nums = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
        res = ""
        num_str = str(int(num))[::-1]
        for i in range(0, len(num_str), 4):
            chunk = num_str[i:i+4]
            chunk_res = ""
            for j, n in enumerate(chunk):
                if n != '0':
                    chunk_res = nums[int(n)] + units[j] + chunk_res
            if chunk_res:
                res = chunk_res + big_units[i//4] + res
        return f"{res}원"
    except:
        return "영원"

# 1. 화면 설정
st.set_page_config(page_title="애드쿠아 외주계약 시스템 v1.1", layout="wide")

# 2. 세션 상태 초기화
if 'step' not in st.session_state: st.session_state.step = 1
if 'contract_party' not in st.session_state: st.session_state.contract_party = "corporation"
if 'contract_type' not in st.session_state: st.session_state.contract_type = ""
if 'generated_doc' not in st.session_state: st.session_state.generated_doc = None

st.title("🛡️ 애드쿠아인터렉티브 외주계약서 생성 시스템")

# ---------------------------------------------------------
# [공지] 시스템 이용 안내 문구 추가
# ---------------------------------------------------------
st.info(
    """
    **💡 이용 안내사항**  
    본 외주계약 생성 프로그램은 **2026년 6월 17일 배포된 [애드쿠아인터렉티브 표준계약 v1.1] 양식**을 사용하는 거래 건에 대해서만 적용됩니다.  
    이 외 다른 양식을 사용하거나 특이사항 반영이 필요한 건은 본 프로그램을 이용하지 마시고 별도로 작성해 주시기 바랍니다.
    """
)
st.divider()

# ---------------------------------------------------------
# [STEP 1] 계약 유형 선택
# ---------------------------------------------------------
if st.session_state.step == 1:
    st.subheader("❓ 계약 유형을 확인합니다.")
    
    # [1번 질문] 
    party_choice = st.radio(
        "1. 계약 대상 주체가 누구인가요?",
        ["🔽 선택해 주세요", "법인/사업자 (사업자등록 보유)", "개인 (사업자등록 미보유)"],
        index=0,
        key="q_party"
    )

    # 1번이 선택되었을 때만 이후 단계 진행
    if party_choice != "🔽 선택해 주세요":
        
        # ─── 법인/사업자 분기 ───
        if "법인" in party_choice:
            st.divider()
            # [2번 질문] 
            nature_choice = st.radio(
                "2. 계약의 성격이 무엇입니까?",
                ["🔽 선택해 주세요", "신규계약", "변경계약 (기존 계약의 조건 변경)"],
                index=0
            )
            
            # 2번이 선택되었을 때만 다음 진입
            if nature_choice != "🔽 선택해 주세요":
                st.divider()
                
                if "변경" in nature_choice:
                    st.session_state.contract_type = "corp_amend"
                    st.success("✅ **[변경계약서]** 양식이 최종 확정되었습니다.")
                    
                elif "신규" in nature_choice:
                    # [3번 질문]
                    is_annual_target = st.radio(
                        "3. 해당 업체와 이미 [기본계약_연간계약]을 체결한 상태입니까?", 
                        ["🔽 선택해 주세요", "예 (기존 체결완료 -> 개별계약 진행)", "아니오 (미체결)"],
                        index=0
                    )
                    
                    st.link_button(
                        "🔍 구글에서 연간계약 체결 리스트 확인하기", 
                        "https://docs.google.com/spreadsheets/d/1ZKkxw6tqTa5d8BHi0ASYwMjW8WC3kawq1SNT6V7VRTk/edit?gid=0#gid=0" 
                    )
                    
                    # 3번이 선택되었을 때만 다음 진입
                    if is_annual_target != "🔽 선택해 주세요":
                        st.divider()
                        if "예" in is_annual_target:
                            st.session_state.contract_type = "corp_single"
                            st.info("✅ **[개별계약서 (기존 연간계약 체결 완료)]** 양식이 최종 확정되었습니다.")
                        else:
                            # 4번 질문 분기
                            st.warning("⚠️ 기본계약 미체결 업체입니다. 새로 체결할 계약 형식을 선택하세요.")
                            sub_choice = st.radio(
                                "4. 어떤 계약을 진행하시겠습니까?", 
                                ["기본계약_연간계약 체결", "표준계약_개별계약 체결"]
                            )
                            if "연간계약" in sub_choice:
                                st.session_state.contract_type = "corp_annual"
                            else:
                                st.session_state.contract_type = "corp"
                            st.success("✅ 양식 선택이 완료되었습니다. 아래 이동 버튼을 눌러주세요.")
        else:
            st.session_state.contract_type = "individual"
            st.info("✅ **[개인 외주계약서]** 양식이 적용됩니다.")

        # 최종 이동 버튼은 1번이라도 선택되어야 하단에 등장
        st.write("")
        if st.button("정보 입력 단계로 이동 ➡️", type="primary", use_container_width=True):
            st.session_state.contract_party = "corporation" if "법인" in party_choice else "individual"
            st.session_state.step = 2
            st.session_state.generated_doc = None
            st.rerun()

# ---------------------------------------------------------
# [STEP 2] 정보 입력 페이지
# ---------------------------------------------------------
elif st.session_state.step == 2:
    party_label = "개인" if st.session_state.contract_party == "individual" else "법인/사업자"
    st.write(f"### ✍️ 2단계. [{party_label}] 정보 입력")
    
    if st.button("⬅️ 이전 단계로"):
        st.session_state.step = 1
        st.rerun()

    st.divider()

    # --- [A. 실시간 반영 영역] ---
    st.subheader("💰 계약 금액 및 프로젝트 정보")
    amt_col1, amt_col2, amt_col3 = st.columns(3)
    with amt_col1:
        amount_val = st.number_input("총 계약금액 (숫자)", min_value=0, step=1000)
    with amt_col2:
        st.text_input("입력된 금액 (콤마)", value=f"{amount_val:,}원", disabled=True)
    with amt_col3:
        amount_kr = format_ko_money(amount_val)
        st.text_input("총 계약금액 (한글)", value=amount_kr, disabled=True)

    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("프로젝트명")
        project_code = st.text_input("프로젝트코드 (숫자 10자리)")
        if project_code and (not project_code.isdigit() or len(project_code) != 10):
            st.warning("⚠️ 프로젝트코드는 숫자 10자리로 정확하게 입력해주세요.")
        contract_title = st.text_input("계약건명")
    with col2:
        contract_start = st.date_input("계약 시작일")

        if st.session_state.contract_type == "corp_annual":
            st.text_input("납품 예정일", value="개별계약에 따름", disabled=True)
            delivery_date_val = None
        else:
            delivery_date_val = st.date_input("납품 예정일")

    st.divider()

    # 레이블 설정
    if st.session_state.contract_party == "individual":
        l_name, l_info, l_addr = "계약자 이름", "생년월일 (예: 1990.01.01)", "계약자 주소"
    else:
        l_name, l_info, l_addr = "수급사업자 회사명", "대표이사 성함", "수급사업자 주소"

    # --- [B. 상세 정보 입력 폼] ---
    prepay_val = 0
    balance_val = 0
    prepay_rate = "0%"
    balance_rate = "0%"
    prepay_date = datetime.now()
    balance_date = datetime.now()

    if st.session_state.contract_party == "corporation":
        st.subheader("💵 대금 지급 세부 일정")
        st.caption("선금을 입력 후 엔터를 치면 선금 청구기일이 생성됩니다. 선금 지급액이 없으면 0을 입력해주세요. 선금+잔금의 합은 총 계약금액과 일치해야 합니다.")

        p_col1, p_col2, p_col3, p_col4 = st.columns([3, 1.5, 3, 1.5])
        
        # 1. 선금 금액 & 선금 청구기일
        with p_col1:
            prepay_val = st.number_input("선금 금액", min_value=0, value=0)
            if prepay_val > 0:
                prepay_date = st.date_input("선금 청구기일 ")
            else:
                prepay_date = None

        # 2. 선금 비율 입력
        with p_col2:
            raw_p_rate = st.number_input("선금 비율 (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.1f", key="input_p_rate")
            prepay_rate = f"{raw_p_rate:.1f}%".replace(".0%", "%")

        # 3. 잔금 비율 계산 (선금 비율이 0일 때는 100% 대신 0%로 표시)
        if raw_p_rate > 0:
            raw_b_rate = max(0.0, 100.0 - raw_p_rate)
            balance_rate = f"{raw_b_rate:.1f}%".replace(".0%", "%")
        else:
            balance_rate = "0%"

        # 4. 잔금 금액 & 잔금 비율(자동계산) 표시
        with p_col3:
            calc_balance_default = max(0, amount_val - prepay_val)
            balance_val = st.number_input("잔금 금액", min_value=0, value=calc_balance_default)
            balance_date = st.date_input("잔금 청구기일 (⚠️ 납품 예정일과 동일하게 작성합니다.)")

        with p_col4:
            st.text_input("잔금 비율 (자동계산)", value=balance_rate, disabled=True, key="disp_b_rate")
            
        # 검증 문구
        if prepay_val + balance_val != amount_val:
            st.warning(f"⚠️ 금액 불일치: 현재 합계 {prepay_val + balance_val:,}원 / 총 계약금액 {amount_val:,}원")
        if delivery_date_val != balance_date:
            st.warning(f"📅 날짜 확인 필요: 납품 예정일({delivery_date_val.strftime('%m/%d')})과 잔금 청구기일({balance_date.strftime('%m/%d')})이 일치하지 않습니다.")

    st.divider()
    
    st.subheader("🏢 상대방 및 계좌 정보")
    c1, c2 = st.columns(2)
    with c1:
        partner_name = st.text_input(l_name)
        partner_address = st.text_input(l_addr)
        partner_info = st.text_input(l_info)
    with c2:
        bank = st.text_input("은행명")
        bank_account = st.text_input("계좌번호")
        # [수정 완료] help 인자를 text_input 내부 파라미터로 올바르게 포함
        account_holder = st.text_input(
            "예금주", 
            help="대금 지급 오류 방지를 위해 반드시 계약자 명의와 일치하는지 확인해주세요."
        )

    # --- [D. 요약 테이블] ---
    st.divider()
    st.subheader("📋 입력 정보 요약 확인")

    if prepay_val > 0:
        payment_detail = f"\n- 선금: {prepay_val:,}원 ({prepay_rate})\n- 잔금: {balance_val:,}원 ({balance_rate})"
    else:
        payment_detail = ""
    
    summary_data = [
        {"항목": "프로젝트명", "내용": project_name},
        {"항목": "계약건명", "내용": contract_title},
        {"항목": "계약 상대방", "내용": partner_name},
        {"항목": "총 계약금액", "내용": f"{amount_val:,}원 ({amount_kr}){payment_detail}"},
        {"항목": "계약 기간", "내용": f"{contract_start} ~ 대금 지급 완료시까지"},
        {"항목": "납품예정일자", "내용": f"{delivery_date_val}"},
        {"항목": "지급 계좌", "내용": f"{bank} {bank_account} (예금주: {account_holder})"}
    ]

    st.table(pd.DataFrame(summary_data))

    submitted = st.button("📄 위 내용으로 계약서 생성하기", type="primary", use_container_width=True)

    # --- [C. 생성 및 검증 로직] ---
    if submitted:
        if not project_name or not partner_name or amount_val == 0:
            st.error("❌ 필수 정보(프로젝트명, 상대방, 계약금액)를 모두 입력해주세요.")
        elif not project_code.isdigit() or len(project_code) != 10:
            st.error("❌ 프로젝트코드는 숫자 10자리여야 계약서를 생성할 수 있습니다.")
        elif st.session_state.contract_party == "corporation" and (prepay_val + balance_val != amount_val):
            st.error(f"❌ 금액 불일치: 선금+잔금({prepay_val + balance_val:,})이 총 계약금액({amount_val:,})과 다릅니다.")
        else:
            try:
                # [수정 완료] STEP 1에서 분기된 contract_type 변수에 따라 정확한 템플릿 매핑
                if st.session_state.contract_party == "individual":
                    t_name = "template_individual.docx"
                else:
                    if st.session_state.contract_type == "corp_amend":
                        t_name = "template_corp_amend.docx"
                    elif st.session_state.contract_type == "corp_single":
                        t_name = "template_corp_single.docx"
                    elif st.session_state.contract_type == "corp_annual":
                        t_name = "template_corp_annual.docx"
                    elif st.session_state.contract_type == "corp":
                        t_name = "template_corp.docx"
                    else:
                        t_name = "template_corp_single.docx"

                doc = DocxTemplate(t_name)
                date_fmt = "%Y년 %m월 %d일"
                
                # 워드 템플릿에 주입할 데이터 딕셔너리
                context = {
                    "project_name": project_name, "project_code": project_code, "contract_title": contract_title,
                    "amount_val": f"{amount_val:,}", "amount_kr": amount_kr,
                    "contract_start": contract_start.strftime(date_fmt),
                    "delivery_date": delivery_date_val.strftime(date_fmt),
                    "partner_name": partner_name, "partner_address": partner_address,
                    "bank": bank, "bank_account": bank_account, "account_holder": account_holder,
                    
                    # 공백 포함 양식에도 호환되도록 기본 치환 데이터 제공
                    " project_name ": project_name, " project_code ": project_code, " contract_title ": contract_title,
                    " amount_val ": f"{amount_val:,}", " amount_kr ": amount_kr,
                    " contract_start ": contract_start.strftime(date_fmt),
                    " delivery_date ": delivery_date_val.strftime(date_fmt),
                    " partner_name ": partner_name, " partner_address ": partner_address,
                    " bank ": bank, " bank_account ": bank_account, " account_holder ": account_holder
                }

                if st.session_state.contract_party == "individual":
                    context["partner_birth"] = partner_info
                    context[" partner_birth "] = partner_info
                else:
                    context["partner_ceo"] = partner_info
                    context[" partner_ceo "] = partner_info

                    # [수정 완료] 수기 입력받은 선금/잔금 비율을 워드 양식에 전달
                    context["prepay_amount"] = f"{prepay_val:,}" if prepay_val > 0 else "0"
                    context["prepay_rate"] = prepay_rate
                    context["prepay_date"] = prepay_date.strftime(date_fmt) if prepay_date else "-"
                    
                    context["balance_amount"] = f"{balance_val:,}"
                    context["balance_rate"] = balance_rate
                    context["balance_date"] = balance_date.strftime(date_fmt) if balance_date else "-"
                    
                    # 양쪽 공백이 포함된 워드 양식 태그에도 완벽 호환
                    context[" prepay_amount "] = f"{prepay_val:,}" if prepay_val > 0 else "0"
                    context[" prepay_rate "] = prepay_rate
                    context[" prepay_date "] = prepay_date.strftime(date_fmt) if prepay_date else "-"
                    context[" balance_amount "] = f"{balance_val:,}"
                    context[" balance_rate "] = balance_rate
                    context[" balance_date "] = balance_date.strftime(date_fmt) if balance_date else "-"

                doc.render(context)
                bio = io.BytesIO()
                doc.save(bio)
                
                file_string_date = contract_start.strftime("%Y%m%d")
                st.session_state.generated_doc = {
                    "name": f"{project_name}_{partner_name}_{file_string_date}.docx",
                    "data": bio.getvalue()
                }
                st.success("🎉 계약서 생성이 완료되었습니다! 계약서 초안을 다운받은 후 [별첨1]을 추가로 작성해서 마무리해주세요.")
                st.rerun()
                
            except Exception as e:
                st.error(f"파일 생성 중 오류 발생: {e}")

    # [수정 완료] 다운로드 버튼 독립 배치
    if st.session_state.generated_doc:
        st.write("")
        st.download_button(
            label="📥 계약서초안 다운로드", 
            data=st.session_state.generated_doc["data"], 
            file_name=st.session_state.generated_doc["name"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
