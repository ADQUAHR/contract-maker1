import streamlit as st
from docxtpl import DocxTemplate
from datetime import datetime
import io
import pandas as pd

# [함수] 숫자를 한글 금액으로 변환
def format_ko_money(num):
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

# 1. 화면 설정
st.set_page_config(page_title="외주계약서 자동 생성기", layout="wide")

# 2. 세션 상태 초기화
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'contract_party' not in st.session_state:
    st.session_state.contract_party = "corporation"
if 'is_annual' not in st.session_state:
    st.session_state.is_annual = False

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
                ["🔽 선택해 주세요", "신규계약 (신규 프로젝트)", "변경계약 (기존 계약의 조건 변경)"],
                index=0
            )
            
            # 2번이 선택되었을 때만 다음 진입
            if nature_choice != "🔽 선택해 주세요":
                st.divider()
                
                if "변경" in nature_choice:
                    st.session_state.is_amend = True
                    st.session_state.is_annual = False
                    st.success("✅ **[변경계약서]** 양식이 최종 확정되었습니다. 아래 이동 버튼을 눌러주세요.")
                    
                elif "신규" in nature_choice:
                    st.session_state.is_amend = False
                    # [3번 질문]
                    is_annual_target = st.radio(
                        "3. 해당 업체와 이미 [기본계약_연간계약]을 체결한 상태입니까?", 
                        ["🔽 선택해 주세요", "예 (기존 체결완료)", "아니오 (미체결)"],
                        index=0
                    )
                    
                    # 3번이 선택되었을 때만 다음 진입
                    if is_annual_target != "🔽 선택해 주세요":
                        st.divider()
                        
                        if is_annual_target == "예 (기존 체결완료)":
                            st.session_state.is_annual = False
                            st.info("✅ **[개별계약서]** 양식이 최종 확정되었습니다. 아래 이동 버튼을 눌러주세요.")
                        else:
                            # [4번 질문] (4번은 미체결 시 바로 고르는 구조이므로 초기 대기 없음)
                            st.warning("⚠️ 미체결 업체입니다. 새로 체결할 계약 형식을 선택하세요.")
                            sub_choice = st.radio(
                                "4. 어떤 계약을 진행하시겠습니까?", 
                                ["기본계약_연간계약 체결", "표준계약_개별계약 체결"]
                            )
                            st.session_state.is_annual = ("연간계약" in sub_choice)
                            st.success("✅ 양식 선택이 완료되었습니다. 아래 이동 버튼을 눌러주세요.")

        # ─── 개인 분기 ───
        else:
            st.session_state.is_amend = False
            st.session_state.is_annual = False
            st.info("✅ **[개인 외주계약서]** 양식이 적용됩니다. 아래 이동 버튼을 눌러주세요.")

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
        project_code = st.text_input("프로젝트코드")
        contract_title = st.text_input("계약건명")
    with col2:
        contract_start = st.date_input("계약 시작일")
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
    prepay_date = datetime.now()
    balance_date = datetime.now()

    if st.session_state.contract_party == "corporation":
        st.subheader("💵 대금 지급 세부 일정")
        st.caption("선금을 입력 후 엔터를 치면 선금 청구기일이 생성됩니다. 선금 지급액이 없으면 0을 입력해주세요. 선금+잔금의 합은 총 계약금액과 일치해야 합니다.")
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            prepay_val = st.number_input("선금 금액", min_value=0, value=0)
            if prepay_val > 0:
                prepay_date = st.date_input("선금 청구기일 ")
            else:
                prepay_date = None
               
        with p_col2:
            balance_val = st.number_input("잔금 금액", min_value=0, value=0)
            balance_date = st.date_input("잔금 청구기일 (✅ 잔금 청구기일은 납품 예정일과 동일하게 작성합니다.")

        if prepay_val + balance_val !=amount_val:
            st.warning(f"⚠️ 금액 불일치: 현재 합계 {prepay_val + balance_val:,}원 / 총 계약금액 {amount_val:,}원")

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
        account_holder = st.text_input("예금주")
        help=f"대금 지급 오류 방지를 위해 반드시 계약자 명의와 일치하는지 확인해주세요."


    # --- [D. 요약 테이블] ---
    st.divider()
    st.subheader("📋 입력 정보 요약 확인")

    payment_detail = f" (선금: {prepay_val:,}원, 잔금: {balance_val:,}원)" if prepay_val > 0 else ""
    
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
        elif st.session_state.contract_party == "corporation" and (prepay_val + balance_val != amount_val):
            st.error(f"❌ 금액 불일치: 선금+잔금({prepay_val + balance_val:,})이 총 계약금액({amount_val:,})과 다릅니다.")
        else:
            try:
                # 템플릿 선택
                if st.session_state.contract_party == "individual":
                    t_name = "template_individual.docx"
                else:
                    t_name = "template_corporation_annual.docx" if st.session_state.is_annual else "template_corp_single.docx"

                doc = DocxTemplate(t_name)
                date_fmt = "%Y년 %m월 %d일"
                
                context = {
                    "project_name": project_name, "project_code": project_code, "contract_title": contract_title,
                    "amount_val": f"{amount_val:,}", "amount_kr": amount_kr,
                    "contract_period": contract_start.strftime(date_fmt),
                    "delivery_date": delivery_date_val.strftime(date_fmt),
                    "partner_name": partner_name, "partner_address": partner_address,
                    "bank": bank, "bank_account": bank_account, "account_holder": account_holder
                }

                if st.session_state.contract_party == "individual":
                    context["partner_birth"] = partner_info
                else:
                    context["partner_ceo"] = partner_info
                    context["prepay_amount"] = format_ko_money(prepay_val)
                    context["prepay_date"] = prepay_date.strftime(date_fmt)
                    context["balance_amount"] = format_ko_money(balance_val)
                    context["balance_date"] = balance_date.strftime(date_fmt)

                doc.render(context)
                bio = io.BytesIO()
                doc.save(bio)
                st.success("🎉 계약서 생성이 완료되었습니다!")
                st.download_button(label="📥 완성본 다운로드", data=bio.getvalue(), file_name=f"{project_name}_{partner_name}_{contract_start}.docx")
            except Exception as e:
                st.error(f"파일 생성 중 오류 발생: {e}")
