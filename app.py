from datetime import datetime
import io
import pandas as pd
import streamlit as st
from docxtpl import DocxTemplate


# [함수] 숫자를 한글 금액으로 변환
def format_ko_money(num):
    try:
        if not num or num == 0:
            return "영원"
        units = ["", "십", "백", "천"]
        big_units = ["", "만", "억", "조"]
        nums = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
        res = ""
        num_str = str(int(num))[::-1]
        for i in range(0, len(num_str), 4):
            chunk = num_str[i : i + 4]
            chunk_res = ""
            for j, n in enumerate(chunk):
                if n != "0":
                    chunk_res = nums[int(n)] + units[j] + chunk_res
            if chunk_res:
                res = chunk_res + big_units[i // 4] + res
        return f"{res}원"
    except Exception:
        return "영원"


# 1. 화면 설정
st.set_page_config(page_title="애드쿠아 외주계약 시스템 v1.1", layout="wide")

# 2. 세션 상태 초기화
if "step" not in st.session_state:
    st.session_state.step = 1
if "contract_party" not in st.session_state:
    st.session_state.contract_party = "corporation"
if "contract_type" not in st.session_state:
    st.session_state.contract_type = ""
if "generated_doc" not in st.session_state:
    st.session_state.generated_doc = None

st.title("🛡️ 애드쿠아인터렉티브 외주계약서 생성 시스템")

# ---------------------------------------------------------
# [공지] 시스템 이용 안내 문구
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

    party_choice = st.radio(
        "1. 계약 대상 주체가 누구인가요?",
        ["🔽 선택해 주세요", "법인/사업자 (사업자등록 보유)", "개인 (사업자등록 미보유)"],
        index=0,
        key="q_party",
    )

    if party_choice != "🔽 선택해 주세요":
        if "법인" in party_choice:
            st.divider()
            nature_choice = st.radio(
                "2. 계약의 성격이 무엇입니까?",
                [
                    "🔽 선택해 주세요",
                    "신규계약",
                    "변경계약 (기존 계약의 조건 변경)",
                ],
                index=0,
            )

            if nature_choice != "🔽 선택해 주세요":
                st.divider()

                if "변경" in nature_choice:
                    st.session_state.contract_type = "corp_amend"
                    st.success(
                        "✅ **[변경계약서]** 양식이 최종 확정되었습니다."
                    )

                elif "신규" in nature_choice:
                    is_annual_target = st.radio(
                        "3. 해당 업체와 이미 [기본계약_연간계약]을 체결한 상태입니까?",
                        [
                            "🔽 선택해 주세요",
                            "예 (기존 체결완료 -> 개별계약 진행)",
                            "아니오 (미체결)",
                        ],
                        index=0,
                    )

                    st.link_button(
                        "🔍 구글에서 연간계약 체결 리스트 확인하기",
                        "https://docs.google.com/spreadsheets/d/1ZKkxw6tqTa5d8BHi0ASYwMjW8WC3kawq1SNT6V7VRTk/edit?gid=0#gid=0",
                    )

                    if is_annual_target != "🔽 선택해 주세요":
                        st.divider()
                        if "예" in is_annual_target:
                            st.session_state.contract_type = "corp_single"
                            st.info(
                                "✅ **[개별계약서 (기존 연간계약 체결 완료)]** 양식이 최종 확정되었습니다."
                            )
                        else:
                            st.warning(
                                "⚠️ 기본계약 미체결 업체입니다. 새로 체결할 계약 형식을 선택하세요."
                            )
                            sub_choice = st.radio(
                                "4. 어떤 계약을 진행하시겠습니까?",
                                ["기본계약_연간계약 체결", "표준계약_개별계약 체결"],
                            )
                            if "연간계약" in sub_choice:
                                st.session_state.contract_type = "corp_annual"
                            else:
                                st.session_state.contract_type = "corp"
                            st.success(
                                "✅ 양식 선택이 완료되었습니다. 아래 이동 버튼을 눌러주세요."
                            )
        else:
            st.session_state.contract_type = "individual"
            st.info("✅ **[개인 외주계약서]** 양식이 적용됩니다.")

        st.write("")
        if st.button(
            "정보 입력 단계로 이동 ➡️", type="primary", use_container_width=True
        ):
            st.session_state.contract_party = (
                "corporation" if "법인" in party_choice else "individual"
            )
            st.session_state.step = 2
            st.session_state.generated_doc = None
            st.rerun()


# ---------------------------------------------------------
# [STEP 2] 정보 입력 페이지
# ---------------------------------------------------------
elif st.session_state.step == 2:
    party_label = (
        "개인"
        if st.session_state.contract_party == "individual"
        else "법인/사업자"
    )
    st.write(f"### ✍️ 2단계. [{party_label}] 정보 입력")

    if st.button("⬅️ 이전 단계로"):
        st.session_state.step = 1
        st.rerun()

    st.divider()

    # --- [A. 프로젝트 정보 및 기본계약 정보] ---
    st.subheader("💰 프로젝트 정보 및 계약 정보")

    contract_start = None
    delivery_date_val = None

    if st.session_state.contract_type == "corp_amend":
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            project_name = st.text_input("프로젝트명")
        with col_p2:
            project_code = st.text_input("프로젝트코드 (숫자 10자리)")
            if project_code and (
                not project_code.isdigit() or len(project_code) != 10
            ):
                st.warning("⚠️ 프로젝트코드는 숫자 10자리로 정확하게 입력해주세요.")
    else:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            project_name = st.text_input("프로젝트명")
        with col_p2:
            contract_start = st.date_input("계약 시작일")

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            project_code = st.text_input("프로젝트코드 (숫자 10자리)")
            if project_code and (
                not project_code.isdigit() or len(project_code) != 10
            ):
                st.warning("⚠️ 프로젝트코드는 숫자 10자리로 정확하게 입력해주세요.")
        with col_c2:
            if st.session_state.contract_type == "corp_annual":
                st.text_input(
                    "납품 예정일", value="개별계약에 따름", disabled=True
                )
                delivery_date_val = None
            else:
                delivery_date_val = st.date_input("납품 예정일")

    contract_title = st.text_input("계약건명")

    amount_val = 0
    amount_kr = ""
    if st.session_state.contract_type != "corp_amend":
        st.write("")
        if st.session_state.contract_type == "corp_annual":
            annual_amount_msg = (
                "계약금액은 [별첨1]의 기본단가표를 근거로 각 개별계약에 따라 산정된다."
            )
            st.text_input("총 계약금액", value=annual_amount_msg, disabled=True)
            amount_kr = annual_amount_msg
        else:
            amt_col1, amt_col2, amt_col3 = st.columns(3)
            with amt_col1:
                amount_val = st.number_input(
                    "총 계약금액 (숫자)", min_value=0, step=1000
                )
            with amt_col2:
                st.text_input(
                    "입력된 금액 (콤마)", value=f"{amount_val:,}원", disabled=True
                )
            with amt_col3:
                amount_kr = format_ko_money(amount_val)
                st.text_input(
                    "총 계약금액 (한글)", value=amount_kr, disabled=True
                )

    st.divider()

    # --- [B. 변경계약 전용 입력 구역 (corp_amend)] ---
    amend_context_extra = {}

    if st.session_state.contract_type == "corp_amend":
        st.subheader("📑 변경계약 세부 정보")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            orig_period_date = st.date_input("원계약 체결일자")
            original_period_str = orig_period_date.strftime("%Y년 %m월 %d일")
        with col_m2:
            amend_period_date = st.date_input("변경 계약일자")

        st.write("")
        selected_changes = st.multiselect(
            "🛠️ 변경이 발생하는 항목을 선택하세요 (다중 선택 가능)",
            ["1. 계약 금액 변경", "2. 계약 내용(과업) 변경", "3. 목적물 납기일 변경"],
            default=["1. 계약 금액 변경"],
        )

        st.divider()

        # 1. 계약 금액 변경
        orig_prepay, new_prepay = 0, 0
        orig_balance, new_balance = 0, 0
        orig_p_date_str, new_p_date_str = "-", "-"
        orig_b_date_str, new_b_date_str = "-", "-"

        if "1. 계약 금액 변경" in selected_changes:
            st.markdown("#### 💰 [변경 내용 1] 계약 금액 변경")

            has_prepay = st.radio(
                "선금(계약금) 유무 선택",
                ["선금(계약금) 없음 (잔금만 변경)", "선금(계약금) 있음 (선금+잔금 변경)"],
                index=0,
                horizontal=True,
            )
            st.write("")

            if "없음" in has_prepay:
                mc1, mc2, mc3 = st.columns([1.5, 3, 3])
                with mc1:
                    st.caption("구분")
                    st.write("**잔금 (합계)**")
                with mc2:
                    st.caption("당초 금액 및 지급 기한")
                    orig_balance = st.number_input(
                        "당초 잔금", min_value=0, value=0, step=10000
                    )
                    orig_b_date = st.date_input("당초 잔금 지급기한", key="obd_only")
                    orig_b_date_str = orig_b_date.strftime("%Y년 %m월 %d일")
                with mc3:
                    st.caption("변경 금액 및 지급 기한")
                    new_balance = st.number_input(
                        "변경 잔금", min_value=0, value=0, step=10000
                    )
                    new_b_date = st.date_input("변경 잔금 지급기한", key="nbd_only")
                    new_b_date_str = new_b_date.strftime("%Y년 %m월 %d일")

            else:
                mc1, mc2, mc3 = st.columns([1.5, 3, 3])
                with mc1:
                    st.caption("구분")
                    st.write("**계약금(선금)**")
                    st.write("")
                    st.write("")
                    st.write("**잔금**")
                with mc2:
                    st.caption("당초 금액 및 지급 기한")
                    orig_prepay = st.number_input(
                        "당초 선금", min_value=0, value=0, step=10000
                    )
                    orig_p_date = st.date_input("당초 선금 지급기한", key="opd")
                    orig_balance = st.number_input(
                        "당초 잔금", min_value=0, value=0, step=10000
                    )
                    orig_b_date = st.date_input("당초 잔금 지급기한", key="obd")

                    orig_p_date_str = orig_p_date.strftime("%Y년 %m월 %d일")
                    orig_b_date_str = orig_b_date.strftime("%Y년 %m월 %d일")

                with mc3:
                    st.caption("변경 금액 및 지급 기한")
                    new_prepay = st.number_input(
                        "변경 선금", min_value=0, value=0, step=10000
                    )
                    new_p_date = st.date_input("변경 선금 지급기한", key="npd")
                    new_balance = st.number_input(
                        "변경 잔금", min_value=0, value=0, step=10000
                    )
                    new_b_date = st.date_input("변경 잔금 지급기한", key="nbd")

                    new_p_date_str = new_p_date.strftime("%Y년 %m월 %d일")
                    new_b_date_str = new_b_date.strftime("%Y년 %m월 %d일")

            st.divider()

        # 2. 계약 내용(과업) 변경
        orig_task_str, new_task_str = "-", "-"
        if "2. 계약 내용(과업) 변경" in selected_changes:
            st.markdown("#### 📝 [변경 내용 2] 계약 내용(과업) 변경")
            tc1, tc2 = st.columns(2)
            with tc1:
                orig_task_str = st.text_area(
                    "'원계약' 과업 내용",
                    placeholder="기존 계약상의 과업 범위를 입력하세요.",
                )
            with tc2:
                new_task_str = st.text_area(
                    "'변경' 과업 내용", placeholder="변경되는 과업 범위를 입력하세요."
                )
            st.divider()

        # 3. 목적물 납기일 변경
        orig_del_ymd_str, new_del_ymd_str = "-", "-"
        if "3. 목적물 납기일 변경" in selected_changes:
            st.markdown("#### 📅 [변경 내용 3] 목적물 납기일 변경")
            dc1, dc2 = st.columns(2)
            with dc1:
                orig_del_date = st.date_input("당초 목적물 납기일")
                orig_del_ymd_str = orig_del_date.strftime("%Y년 %m월 %d일")
            with dc2:
                new_del_date = st.date_input("변경 목적물 납기일")
                new_del_ymd_str = new_del_date.strftime("%Y년 %m월 %d일")
            st.divider()

        amend_context_extra = {
            "original_period": original_period_str,
            "amend_period": amend_period_date.strftime("%Y년 %m월 %d일"),
            "orig_prepay": f"{orig_prepay:,}" if orig_prepay > 0 else "0",
            "new_prepay": f"{new_prepay:,}" if new_prepay > 0 else "0",
            "orig_prepay_date": orig_p_date_str,
            "new_prepay_date": new_p_date_str,
            "orig_balance": f"{orig_balance:,}",
            "new_balance": f"{new_balance:,}",
            "orig_balance_date": orig_b_date_str,
            "new_balance_date": new_b_date_str,
            "orig_total": f"{(orig_prepay + orig_balance):,}",
            "new_total": f"{(new_prepay + new_balance):,}",
            "orig_task": orig_task_str,
            "new_task": new_task_str,
            "orig_delivery_ymd": orig_del_ymd_str,
            "new_delivery_ymd": new_del_ymd_str,
        }

    # --- [C. 일반 대금 지급 세부 일정 (신규 계약 전용)] ---
    prepay_val = 0
    balance_val = 0
    prepay_rate = "0%"
    balance_rate = "0%"
    prepay_date = None
    balance_date = None

    if (
        st.session_state.contract_party == "corporation"
        and st.session_state.contract_type
        not in ["corp_annual", "corp_amend"]
    ):
        st.subheader("💵 대금 지급 세부 일정")
        st.caption(
            "선금을 입력 후 엔터를 치면 선금 청구기일이 생성됩니다. 선금 지급액이 없으면 0을 입력해주세요."
        )

        p_col1, p_col2, p_col3, p_col4 = st.columns([3, 1.5, 3, 1.5])

        with p_col1:
            prepay_val = st.number_input("선금 금액", min_value=0, value=0)
            if prepay_val > 0:
                prepay_date = st.date_input("선금 청구기일 ")
            else:
                prepay_date = None

        with p_col2:
            raw_p_rate = st.number_input(
                "선금 비율 (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.1,
                format="%.1f",
                key="input_p_rate",
            )
            prepay_rate = f"{raw_p_rate:.1f}%".replace(".0%", "%")

        if raw_p_rate > 0:
            raw_b_rate = max(0.0, 100.0 - raw_p_rate)
            balance_rate = f"{raw_b_rate:.1f}%".replace(".0%", "%")
        else:
            balance_rate = "0%"

        with p_col3:
            calc_balance_default = max(0, amount_val - prepay_val)
            balance_val = st.number_input(
                "잔금 금액", min_value=0, value=calc_balance_default
            )
            balance_date = st.date_input(
                "잔금 청구기일 (⚠️ 납품 예정일과 동일하게 작성합니다.)"
            )

        with p_col4:
            st.text_input(
                "잔금 비율 (자동계산)",
                value=balance_rate,
                disabled=True,
                key="disp_b_rate",
            )

        if prepay_val + balance_val != amount_val:
            st.warning(
                f"⚠️ 금액 불일치: 현재 합계 {prepay_val + balance_val:,}원 / 총 계약금액 {amount_val:,}원"
            )
        if delivery_date_val and delivery_date_val != balance_date:
            st.warning(
                f"📅 날짜 확인 필요: 납품 예정일({delivery_date_val.strftime('%m/%d')})과 잔금 청구기일({balance_date.strftime('%m/%d')})이 일치하지 않습니다."
            )

        st.divider()

    # --- [D. 상대방 및 계좌 정보] ---
    st.subheader("🏢 상대방 정보")

    bank, bank_account, account_holder = "", "", ""

    if st.session_state.contract_party == "individual":
        l_name, l_info, l_addr = (
            "계약자 이름",
            "생년월일 (예: 1990.01.01)",
            "계약자 주소",
        )
    else:
        l_name, l_info, l_addr = (
            "수급사업자 회사명",
            "대표이사 성함",
            "수급사업자 주소",
        )

    if st.session_state.contract_type == "corp_amend":
        partner_name = st.text_input(l_name)
        partner_info = st.text_input(l_info)
        partner_address = st.text_input(l_addr)
    else:
        col3, col4 = st.columns(2)
        with col3:
            partner_name = st.text_input(l_name)
            partner_info = st.text_input(l_info)
            partner_address = st.text_input(l_addr)
        with col4:
            bank = st.text_input("지급 은행")
            bank_account = st.text_input("계좌번호")
            account_holder = st.text_input("예금주")

    # --- [E. 요약 테이블] ---
    st.divider()
    st.subheader("📋 입력 정보 요약 확인")

    if st.session_state.contract_type == "corp_annual":
        summary_amount_str = "계약금액은 [별첨1]의 기본단가표를 근거로 각 개별계약에 따라 산정된다."
        summary_delivery_str = "개별계약에 따름"
        summary_period_str = f"{contract_start} ~ 대금 지급 완료시까지"
        summary_bank_str = f"{bank} {bank_account} (예금주: {account_holder})"
    elif st.session_state.contract_type == "corp_amend":
        summary_amount_str = "변경계약서 표 참조"
        summary_delivery_str = (
            amend_context_extra.get("new_delivery_ymd", "원계약 조건 따름")
            if amend_context_extra.get("new_delivery_ymd") != "-"
            else "원계약 조건 따름"
        )
        summary_period_str = f"원계약일: {amend_context_extra.get('original_period', '-')} / 변경계약일: {amend_context_extra.get('amend_period', '-')}"
        summary_bank_str = "원계약 계좌 적용 (입력 생략)"
    else:
        summary_amount_str = f"{amount_val:,}원 ({amount_kr})"
        if prepay_val > 0:
            summary_amount_str += f"<br>- 선금: {prepay_val:,}원 ({prepay_rate})<br>- 잔금: {balance_val:,}원 ({balance_rate})"
        summary_delivery_str = f"{delivery_date_val}"
        summary_period_str = f"{contract_start} ~ 대금 지급 완료시까지"
        summary_bank_str = f"{bank} {bank_account} (예금주: {account_holder})"

    summary_data = [
        {"항목": "프로젝트명", "내용": project_name},
        {"항목": "프로젝트코드", "내용": project_code},
        {"항목": "계약건명", "내용": contract_title},
        {"항목": "계약 상대방", "내용": partner_name},
        {"항목": "총 계약금액", "내용": summary_amount_str},
        {"항목": "계약 기간/일자", "내용": summary_period_str},
        {"항목": "납품예정일자", "내용": summary_delivery_str},
        {"항목": "지급 계좌", "내용": summary_bank_str},
    ]

    table_html = "<table style='width:100%; border-collapse:collapse; margin-bottom:1.5rem;'>"
    for row in summary_data:
        table_html += (
            f"<tr style='border-bottom: 1px solid #e2e8f0;'>"
            f"<td style='width: 20%; padding: 10px; font-weight: bold; background-color: #f8fafc; color: #334155; white-space: nowrap;'>{row['항목']}</td>"
            f"<td style='width: 80%; padding: 10px; color: #1e293b;'>{row['내용']}</td>"
            f"</tr>"
        )
    table_html += "</table>"

    st.markdown(table_html, unsafe_allow_html=True)

    submitted = st.button(
        "📄 위 내용으로 계약서 생성하기", type="primary", use_container_width=True
    )

    # --- [F. 생성 및 검증 로직] ---
    if submitted:
        is_amount_invalid = (
            st.session_state.contract_type
            not in ["corp_annual", "corp_amend"]
        ) and (amount_val == 0)

        if not project_name or not partner_name or is_amount_invalid:
            st.error("❌ 필수 정보(프로젝트명, 상대방, 계약금액)를 모두 입력해주세요.")

        elif not project_code.isdigit() or len(project_code) != 10:
            st.error(
                "❌ 프로젝트코드는 숫자 10자리여야 계약서를 생성할 수 있습니다."
            )

        elif (
            st.session_state.contract_party == "corporation"
            and st.session_state.contract_type
            not in ["corp_annual", "corp_amend"]
            and (prepay_val + balance_val != amount_val)
        ):
            st.error(
                f"❌ 금액 불일치: 선금+잔금({prepay_val + balance_val:,})이 총 계약금액({amount_val:,})과 다릅니다."
            )

        else:
            try:
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

                if st.session_state.contract_type == "corp_annual":
                    delivery_str = "개별계약에 따름"
                    amount_display = "계약금액은 [별첨1]의 기본단가표를 근거로 각 개별계약에 따라 산정된다."
                    start_str = contract_start.strftime(date_fmt)
                elif st.session_state.contract_type == "corp_amend":
                    delivery_str = amend_context_extra.get(
                        "new_delivery_ymd", "개별계약에 따름"
                    )
                    amount_display = "변경계약서 표 참조"
                    start_str = "-"
                else:
                    delivery_str = (
                        delivery_date_val.strftime(date_fmt)
                        if delivery_date_val
                        else "개별계약에 따름"
                    )
                    amount_display = f"{amount_val:,}"
                    start_str = contract_start.strftime(date_fmt)

                context = {
                    "project_name": project_name,
                    "project_code": project_code,
                    "contract_title": contract_title,
                    "amount_val": amount_display,
                    "amount_kr": amount_kr,
                    "contract_start": start_str,
                    "delivery_date": delivery_str,
                    "partner_name": partner_name,
                    "partner_address": partner_address,
                    "bank": bank,
                    "bank_account": bank_account,
                    "account_holder": account_holder,
                    "prepay_amount": (
                        f"{prepay_val:,}" if prepay_val > 0 else "0"
                    ),
                    "prepay_rate": prepay_rate,
                    "prepay_date": (
                        prepay_date.strftime(date_fmt) if prepay_date else "-"
                    ),
                    "balance_amount": f"{balance_val:,}",
                    "balance_rate": balance_rate,
                    "balance_date": (
                        balance_date.strftime(date_fmt)
                        if balance_date
                        else "-"
                    ),
                    " project_name ": project_name,
                    " project_code ": project_code,
                    " contract_title ": contract_title,
                    " amount_val ": amount_display,
                    " amount_kr ": amount_kr,
                    " contract_start ": start_str,
                    " delivery_date ": delivery_str,
                    " partner_name ": partner_name,
                    " partner_address ": partner_address,
                    " bank ": bank,
                    " bank_account ": bank_account,
                    " account_holder ": account_holder,
                    " prepay_amount ": (
                        f"{prepay_val:,}" if prepay_val > 0 else "0"
                    ),
                    " prepay_rate ": prepay_rate,
                    " prepay_date ": (
                        prepay_date.strftime(date_fmt) if prepay_date else "-"
                    ),
                    " balance_amount ": f"{balance_val:,}",
                    " balance_rate ": balance_rate,
                    " balance_date ": (
                        balance_date.strftime(date_fmt)
                        if balance_date
                        else "-"
                    ),
                }

                if st.session_state.contract_type == "corp_amend":
                    context.update(amend_context_extra)
                    for k, v in list(amend_context_extra.items()):
                        context[f" {k} "] = v

                if st.session_state.contract_party == "individual":
                    context["partner_birth"] = partner_info
                    context[" partner_birth "] = partner_info
                else:
                    context["partner_ceo"] = partner_info
                    context[" partner_ceo "] = partner_info

                doc.render(context)
                bio = io.BytesIO()
                doc.save(bio)

                file_string_date = (
                    amend_context_extra.get("amend_period", "")
                    .replace("년 ", "")
                    .replace("월 ", "")
                    .replace("일", "")
                    if st.session_state.contract_type == "corp_amend"
                    else contract_start.strftime("%Y%m%d")
                )
                st.session_state.generated_doc = {
                    "name": f"{project_name}_{partner_name}_{file_string_date}.docx",
                    "data": bio.getvalue(),
                }
                st.success("🎉 변경계약서 생성이 완료되었습니다!")
                st.rerun()

            except Exception as e:
                st.error(f"파일 생성 중 오류 발생: {e}")


# ---------------------------------------------------------
# [마지막] 다운로드 버튼
# ---------------------------------------------------------
if st.session_state.generated_doc:
    st.write("")
    st.warning("⚠️ 계약서 초안 다운로드 후 [별첨1_세부 용역 내역 및 추가 특약사항]을 추가 작성해주세요.")
    st.download_button(
        label="📥 계약서초안 다운로드",
        data=st.session_state.generated_doc["data"],
        file_name=st.session_state.generated_doc["name"],
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
