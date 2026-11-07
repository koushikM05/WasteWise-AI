"""WasteWise AI dashboard for Team Spark.

Run this file with: streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

import analytics
import hindsight_memory
from ai_agent import ask_agent
from data_manager import DataError, load_records
from hindsight_memory import HindsightMemoryError

PAGES = ["Dashboard", "Daily Records", "AI Food Advisor", "Analytics"]

CHART_COLORS = {
    "Prepared": "#1F7A4D",
    "Sold": "#7DCAA5",
    "Wasted": "#E07A3D",
}


def main():
    """Load the canteen file once, then show the page the user picked."""
    st.set_page_config(
        page_title="WasteWise AI",
        page_icon="🥗",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()
    page = render_sidebar()

    if page == "AI Food Advisor":
        advisor_records, data_problem = load_records_for_advisor()
        render_food_advisor(advisor_records, data_problem)
        return

    try:
        records, warnings = load_records()
    except DataError as error:
        st.error(str(error))
        st.info(
            "Fix the sample file and refresh this page. "
            "The rest of the dashboard stays hidden until the data can be read."
        )
        return

    for warning in warnings:
        st.warning(warning)

    if page == "Dashboard":
        render_dashboard(records)
    elif page == "Daily Records":
        render_daily_records(records)
    else:
        render_analytics(records)


def apply_theme():
    """Green and white styling for the sidebar, titles, and metric cards."""
    st.markdown(
        """
        <style>
            .stApp {
                background: #ffffff;
                color: #163528;
            }
            [data-testid="stSidebar"] {
                background: #145C38;
            }
            [data-testid="stSidebar"] * {
                color: #F4FBF7;
            }
            [data-testid="stSidebar"] hr {
                border-color: rgba(255, 255, 255, 0.25);
            }
            .sidebar-kicker {
                letter-spacing: 0.08em;
                text-transform: uppercase;
                font-size: 0.75rem;
                opacity: 0.8;
                margin-bottom: 0;
            }
            .page-kicker {
                color: #1F7A4D;
                font-size: 0.8rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.15rem;
            }
            .metric-card {
                background: #ffffff;
                border: 1px solid #D7EBDD;
                border-top: 4px solid #1F7A4D;
                border-radius: 14px;
                padding: 0.95rem 1rem 0.85rem;
                min-height: 108px;
            }
            .metric-card .label {
                color: #5E7568;
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                text-transform: uppercase;
            }
            .metric-card .value {
                color: #143D28;
                font-size: 1.85rem;
                font-weight: 700;
                line-height: 1.2;
                margin-top: 0.35rem;
            }
            .metric-card .hint {
                color: #6D8478;
                font-size: 0.82rem;
                margin-top: 0.2rem;
            }
            .metric-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.85rem;
                margin: 0.4rem 0 1.2rem;
            }
            @media (max-width: 1100px) {
                .metric-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
            @media (max-width: 640px) {
                .metric-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    """Show the project name and the four navigation choices."""
    st.sidebar.markdown(
        '<p class="sidebar-kicker">Team Spark</p>', unsafe_allow_html=True
    )
    st.sidebar.markdown("## WasteWise AI")
    st.sidebar.caption("Canteen food-waste dashboard")
    st.sidebar.divider()
    page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption("Sample data: college canteen log, 26 Oct–6 Nov 2026.")
    return page


def render_dashboard(records):
    """Show headline numbers and the prepared / sold / wasted chart."""
    st.markdown('<p class="page-kicker">Overview</p>', unsafe_allow_html=True)
    st.title("Dashboard")
    st.write(
        "These totals come from the sample canteen file. "
        "Waste percentage is wasted portions divided by prepared portions."
    )

    render_metric_cards(analytics.summary(records))
    st.subheader("Prepared, sold, and wasted")
    st.caption("Each day compares the three portion counts side by side.")
    draw_comparison_chart(analytics.portions_by_day(records))


def render_daily_records(records):
    """Show every food row from the sample file."""
    st.markdown('<p class="page-kicker">Records</p>', unsafe_allow_html=True)
    st.title("Daily Records")
    st.write(f"{len(records)} item rows from the canteen log.")
    st.dataframe(
        display_table(records),
        width="stretch",
        hide_index=True,
    )


def load_records_for_advisor():
    """Read the canteen file for the Retain step."""
    try:
        records, _warnings = load_records()
        return records, None
    except DataError as error:
        return None, str(error)


def render_food_advisor(records=None, data_problem=None):
    """Show Hindsight memory tools and the Groq AI advisor."""
    st.markdown('<p class="page-kicker">Assistant</p>', unsafe_allow_html=True)
    st.title("AI Food Advisor")
    st.write(
        "Hindsight provides long-term memory. Retain saves canteen records, "
        "Recall searches saved memories, Reflect generates insights, and "
        "Groq AI Advice combines available context into practical recommendations."
    )

    setup_problem = hindsight_memory.setup_problem()
    render_memory_status(setup_problem)

    retain_tab, recall_tab, reflect_tab, groq_tab = st.tabs(
        ["1. Retain", "2. Recall", "3. Reflect", "4. Groq AI Advice"]
    )

    with retain_tab:
        render_retain_tab(records, data_problem, setup_problem)

    with recall_tab:
        render_recall_tab(setup_problem)

    with reflect_tab:
        render_reflect_tab(setup_problem)

    with groq_tab:
        render_groq_tab(records)


def render_memory_status(setup_problem):
    """Show Hindsight settings without revealing the API key."""
    settings = hindsight_memory.get_settings()
    with st.container(border=True):
        st.markdown("**Hindsight connection**")
        if setup_problem:
            st.warning(setup_problem)
        else:
            st.caption(
                f"Memory bank: `{settings['bank_name']}` · "
                f"Server: `{settings['base_url']}` · "
                "API key: found in .env (hidden)"
            )

        if st.button("Test connection", disabled=bool(setup_problem)):
            with st.spinner("Asking Hindsight for its version..."):
                try:
                    version = hindsight_memory.check_connection()
                    st.session_state["hs_connection"] = (
                        "ok",
                        f"Connected. Hindsight API version {version}.",
                    )
                except HindsightMemoryError as error:
                    st.session_state["hs_connection"] = ("error", str(error))

        state = st.session_state.get("hs_connection")
        if state:
            (st.success if state[0] == "ok" else st.error)(state[1])


def render_retain_tab(records, data_problem, setup_problem):
    """Save canteen rows and optional staff notes into Hindsight."""
    st.subheader("Retain: save canteen records")
    st.write(
        "Each row of the canteen log becomes one memory, written as a plain "
        "sentence with the date, dish, portions prepared, sold and wasted, "
        "and the reason."
    )

    if data_problem:
        st.warning(
            f"The canteen file could not be read, so there is nothing to save. "
            f"{data_problem}"
        )
    else:
        memory_items = hindsight_memory.build_memory_items(records)
        st.metric("Records ready to save", len(memory_items))
        with st.expander("Preview the memories that will be sent"):
            for item in memory_items[:3]:
                st.write(f"• {item['content']}")
            if len(memory_items) > 3:
                st.caption(f"…and {len(memory_items) - 3} more.")

        if st.button(
            "Save canteen records to Hindsight",
            type="primary",
            disabled=bool(setup_problem),
        ):
            bar = st.progress(0.0, text="Saving to Hindsight...")
            try:
                saved = hindsight_memory.retain_records(
                    records,
                    progress=lambda done, total: bar.progress(
                        done / total, text=f"Saved {done} of {total}"
                    ),
                )
                st.session_state["hs_retained"] = saved
                st.success(
                    f"Hindsight accepted {saved} records. Try the Recall tab next."
                )
            except HindsightMemoryError as error:
                bar.empty()
                st.error(str(error))

        if st.session_state.get("hs_retained"):
            st.caption(
                f"Last save in this session: "
                f"{st.session_state['hs_retained']} records."
            )
        st.caption(
            "Each record has a fixed ID (day, meal, dish), so saving again "
            "should update rather than duplicate it. Check your Hindsight "
            "dashboard after your first save to confirm."
        )

    st.divider()
    st.markdown("**Add a staff note**")
    note = st.text_input(
        "Note",
        placeholder="Example: Sports day tomorrow, expect fewer students at lunch.",
        label_visibility="collapsed",
        key="staff_note",
    )
    if st.button("Save note", disabled=bool(setup_problem)):
        if not note.strip():
            st.warning("Enter a note before saving.")
        else:
            try:
                hindsight_memory.retain_memory(note.strip())
                st.success("Note saved to Hindsight memory.")
            except HindsightMemoryError as error:
                st.error(str(error))


def render_recall_tab(setup_problem):
    """Search the memory bank and show matching saved memories."""
    st.subheader("Recall: search saved memories")
    st.write("Ask a question. Hindsight returns the saved memories that best match it.")
    question = st.text_input(
        "Question to search for",
        value="Which dishes were wasted the most?",
        key="recall_question",
    )

    if st.button(
        "Recall memories", type="primary", disabled=bool(setup_problem)
    ):
        with st.spinner("Searching Hindsight memory..."):
            try:
                found = hindsight_memory.recall_memories(question)
                st.session_state["hs_recall"] = {
                    "question": question,
                    "found": found,
                }
            except HindsightMemoryError as error:
                st.session_state.pop("hs_recall", None)
                st.error(str(error))

    result = st.session_state.get("hs_recall")
    if not result:
        return

    if not result["found"]:
        st.info(
            "Hindsight has no saved memories that match this question. "
            "Go to the Retain tab, save the canteen records, then try again."
        )
        return

    st.success(
        f"Hindsight returned {len(result['found'])} saved memories "
        f"for: {result['question']}"
    )
    for number, item in enumerate(result["found"], start=1):
        st.write(f"**{number}.** {item['text']}")
        details = " · ".join(
            part for part in (item.get("when", ""), item.get("type", "")) if part
        )
        if details:
            st.caption(details)


def render_reflect_tab(setup_problem):
    """Ask Hindsight to reason over saved memories."""
    st.subheader("Reflect: insights from memory")
    st.write(
        "Hindsight looks through the saved memories and writes an answer. "
        "The memories it used are listed under the answer so you can check it."
    )
    question = st.text_area(
        "Question for Hindsight",
        value=(
            "Which dishes are wasted the most, and how should we change "
            "how much we prepare?"
        ),
        key="reflect_question",
        height=90,
    )

    if st.button(
        "Reflect on memories", type="primary", disabled=bool(setup_problem)
    ):
        with st.spinner("Hindsight is thinking over the saved memories..."):
            try:
                answer = hindsight_memory.reflect_memories(question)
                st.session_state["hs_reflect"] = {
                    "question": question,
                    "answer": answer,
                }
            except HindsightMemoryError as error:
                st.session_state.pop("hs_reflect", None)
                st.error(str(error))

    result = st.session_state.get("hs_reflect")
    if not result:
        return

    answer = result["answer"]
    if not answer["text"]:
        st.info(
            "Hindsight did not return an answer. "
            "Save the canteen records in the Retain tab first."
        )
        return

    st.markdown("**Hindsight's answer**")
    st.write(answer["text"])

    if answer["memories"]:
        with st.expander(
            f"Based on {len(answer['memories'])} saved memories"
        ):
            for memory in answer["memories"]:
                st.write(f"• {memory}")
    else:
        st.warning(
            "Hindsight did not list any saved memories behind this answer, "
            "so treat it as general advice, not a result from your canteen data. "
            "Save records in the Retain tab and ask again."
        )


def render_groq_tab(records=None):
    """Generate Groq advice using analytics and available Hindsight context."""
    st.subheader("Groq AI Food Advisor")
    st.write(
        "Ask questions about your canteen's food waste. Groq uses the "
        "available analytics and Hindsight memories from this session."
    )

    waste_summary = "Canteen analytics are currently unavailable."

    if records is not None:
        try:
            totals = analytics.summary(records)
            by_item = analytics.waste_by_item(records)

            summary_lines = [
                f"Prepared portions: {totals['prepared']}",
                f"Sold portions: {totals['sold']}",
                f"Wasted portions: {totals['wasted']}",
                f"Waste percentage: {totals['waste_percentage']:.1f}%",
                "",
                "Dish-wise waste:",
            ]

            if not by_item.empty:
                top_items = by_item.sort_values(
                    "portions_wasted", ascending=False
                ).head(5)

                for _, item in top_items.iterrows():
                    summary_lines.append(
                        f"{item['item']}: {item['portions_wasted']} portions wasted"
                    )
            else:
                summary_lines.append("No dish-wise waste records available.")

            waste_summary = "\n".join(summary_lines)
        except Exception as error:
            st.warning(f"Could not prepare analytics summary: {error}")

    # Reuse the most recently retrieved Recall and Reflect results.
    memory_parts = []

    recall_result = st.session_state.get("hs_recall")
    if recall_result:
        for item in recall_result.get("found", []):
            memory_text = item.get("text", "")
            if memory_text:
                memory_parts.append(memory_text)

    reflect_result = st.session_state.get("hs_reflect")
    if reflect_result:
        reflect_answer = reflect_result.get("answer", {})
        reflect_text = reflect_answer.get("text", "")
        if reflect_text:
            memory_parts.append("Hindsight reflection: " + reflect_text)

        for memory in reflect_answer.get("memories", []):
            if memory:
                memory_parts.append(str(memory))

    memories = "\n".join(memory_parts)
    if not memories:
        memories = (
            "No Hindsight memories have been retrieved in this session. "
            "The AI should not claim to have used historical memories."
        )

    question = st.text_area(
        "Ask WasteWise AI",
        placeholder=(
            "Example: Which dishes should we prepare in smaller "
            "quantities tomorrow?"
        ),
        key="groq_question",
        height=100,
    )

    if st.button("Generate AI Advice", type="primary"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Groq is analysing your canteen information..."):
                try:
                    answer = ask_agent(
                        question=question.strip(),
                        waste_summary=waste_summary,
                        memories=memories,
                    )
                    st.session_state["groq_answer"] = answer
                    st.session_state["groq_answer_question"] = question.strip()
                except Exception as error:
                    st.error(f"Groq AI request failed: {error}")

    answer = st.session_state.get("groq_answer")
    if answer:
        st.markdown("### AI Recommendations")
        st.write(answer)

    with st.expander("View information sent to Groq"):
        st.markdown("**Waste analytics**")
        st.text(waste_summary)
        st.markdown("**Hindsight memories**")
        st.text(memories)


def render_analytics(records):
    """Show waste broken down by dish and by meal."""
    totals = analytics.summary(records)
    waste_cost = analytics.cost_of_waste(records)

    st.markdown('<p class="page-kicker">Breakdown</p>', unsafe_allow_html=True)
    st.title("Analytics")
    st.write(
        f"Overall waste is {totals['waste_percentage']:.1f}% of prepared portions. "
        f"Estimated cost of those leftovers is ₹{waste_cost:,.0f}."
    )

    left, right = st.columns(2)
    with left:
        st.subheader("Waste by dish")
        draw_item_chart(analytics.waste_by_item(records))
    with right:
        st.subheader("Waste by meal")
        meal_table = analytics.waste_by_meal(records).rename(
            columns={
                "meal": "Meal",
                "portions_prepared": "Prepared",
                "portions_served": "Sold",
                "portions_wasted": "Wasted",
                "waste_percentage": "Waste %",
            }
        )
        meal_table["Waste %"] = meal_table["Waste %"].map(
            lambda value: f"{value:.1f}%"
        )
        st.dataframe(meal_table, width="stretch", hide_index=True)


def render_metric_cards(totals):
    """Draw the four headline numbers for the dashboard."""
    cards = [
        ("Total food prepared", f"{totals['prepared']:,.0f}", "portions"),
        ("Total food sold", f"{totals['sold']:,.0f}", "portions served"),
        ("Total food wasted", f"{totals['wasted']:,.0f}", "portions left over"),
        (
            "Food waste percentage",
            f"{totals['waste_percentage']:.1f}%",
            "wasted ÷ prepared",
        ),
    ]
    cards_html = "".join(
        f'<div class="metric-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div><div class="hint">{hint}</div></div>'
        for label, value, hint in cards
    )
    st.markdown(
        f'<div class="metric-grid">{cards_html}</div>',
        unsafe_allow_html=True,
    )


def display_table(records):
    """Rename columns so the on-screen table is easy to read."""
    table = records.copy()
    table["date"] = table["date"].dt.strftime("%Y-%m-%d")
    table = table.rename(
        columns={
            "date": "Date",
            "meal": "Meal",
            "item": "Item",
            "category": "Category",
            "portions_prepared": "Prepared",
            "portions_served": "Sold",
            "portions_wasted": "Wasted",
            "waste_kg": "Waste (kg)",
            "cost_per_portion": "Cost per portion (₹)",
            "reason": "Reason",
        }
    )
    number_columns = [
        "Prepared",
        "Sold",
        "Wasted",
        "Waste (kg)",
        "Cost per portion (₹)",
    ]
    for column in number_columns:
        table[column] = pd.to_numeric(table[column])
    return table


def draw_comparison_chart(daily):
    """Grouped bar chart of prepared, sold, and wasted portions by day."""
    long_table = daily.melt(
        id_vars="day",
        value_vars=["Prepared", "Sold", "Wasted"],
        var_name="Status",
        value_name="Portions",
    )
    figure = px.bar(
        long_table,
        x="day",
        y="Portions",
        color="Status",
        barmode="group",
        color_discrete_map=CHART_COLORS,
        category_orders={
            "day": list(daily["day"]),
            "Status": ["Prepared", "Sold", "Wasted"],
        },
    )
    figure.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=8, r=8, t=12, b=8),
        legend_title_text="",
        xaxis_title="",
        yaxis_title="Portions",
        font=dict(color="#163528"),
    )
    figure.update_yaxes(gridcolor="#E6F2EB", zeroline=False)
    st.plotly_chart(figure, width="stretch")


def draw_item_chart(by_item):
    """Horizontal bar chart of wasted portions for each dish."""
    figure = px.bar(
        by_item,
        x="portions_wasted",
        y="item",
        orientation="h",
        color_discrete_sequence=["#1F7A4D"],
    )
    figure.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=8, r=8, t=12, b=8),
        showlegend=False,
        xaxis_title="Portions wasted",
        yaxis_title="",
        yaxis={"categoryorder": "total ascending"},
        font=dict(color="#163528"),
        height=420,
    )
    figure.update_xaxes(gridcolor="#E6F2EB", zeroline=False)
    st.plotly_chart(figure, width="stretch")


if __name__ == "__main__":
    main()