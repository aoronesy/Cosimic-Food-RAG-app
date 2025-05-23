import json
from collections.abc import AsyncIterator

from langchain.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage

from quartapp.approaches.base import ApproachesBase
from quartapp.approaches.schemas import DataPoint


def get_data_points(documents: list[Document]) -> list[DataPoint]:
    data_points: list[DataPoint] = []

    for res in documents:
        raw_data = json.loads(res.page_content)
        json_data_point: DataPoint = DataPoint()
        json_data_point.name = raw_data.get("name")
        json_data_point.description = raw_data.get("description")
        json_data_point.price = raw_data.get("price")
        json_data_point.category = raw_data.get("category")
        data_points.append(json_data_point)
    return data_points


REPHRASE_PROMPT = """\
以下の会話に基づいて、フォローアップ質問を独立した質問に言い換えてください。

チャット履歴:
{chat_history}
フォローアップ質問: {question}
独立した質問:"""

CONTEXT_PROMPT = """\
あなたは勤怠と契約が辻褄が合っているか確認するアシスタントです。​
合っていないところをすべて指摘してください。​
以下は例です。​

# 勤怠簿の例​

2020年11月支払分（対象期間: 2024年10⽉1⽇ 〜 2024年10⽉31⽇）                    ​                   ​

日付    始業時間    休憩時間    終業時間    残業時間    総労働時間​
2025/3/3    9:14    0:51:00    20:11    2:30:00    0 days 10:06:00​
2025/3/4    8:45    0:48:00    20:41    3:00:00    0 days 11:08:00​
2025/3/5    9:21    0:47:00    18:50    0:30:00    0 days 08:42:00​

# 雇用契約書の例​

契約期間​
期間の定め有り（2024年10月1日～2025年9月30日）​

所定労働時間​
始業・終業の時刻 ：（始業）9時00分 ～ （終業）18時00分​
休憩時間 ： 1 時間​
1 週間の所定労働時間 ： 40 時間 00 分​

但し、業務の都合により、始業・終業の時刻を変更する場合がある。​
時間外労働​
所定時間外労働の有無 ： 有​
休日労働の有無 ： 有​
休日​
土曜日、日曜日、祝日、GW、年末年始​
但し、休日を振替えるなどの方法によって休日を変更する場合がある。​

休暇​
年次有給休暇 所定労働日数の 8 割以上出勤し、6 ヶ月以上継続勤務した場合、法定通り​

判断の基準​
従事している業務の進捗状況により判断する​

社会保険等の加入​
労災保険、雇用保険、健康保険、厚生年金​​
​\

# ユーザーの質問
ユーザーの質問: {input}

# チャットボットの応答
チャットボットの応答:"""


class RAG(ApproachesBase):
    async def run(
        self, messages: list, temperature: float, limit: int, score_threshold: float
    ) -> tuple[list[Document], str]:
        context_prompt_template = ChatPromptTemplate.from_template(CONTEXT_PROMPT)
        self._chat.temperature = temperature
        context_chain = context_prompt_template | self._chat
        response = await context_chain.ainvoke({"input": messages[0]["content"]})

        formatted_response = {"response": response.content, "rephrased_response": messages[0]["content"]}

        return [], json.dumps(formatted_response, ensure_ascii=False)

    async def run_stream(
        self, messages: list, temperature: float, limit: int, score_threshold: float
    ) -> tuple[list[Document], AsyncIterator[BaseMessage]]:
        # Create a vector store retriever
        # retriever = self._vector_store.as_retriever(
        #    search_type="similarity", search_kwargs={"k": limit, "score_threshold": score_threshold}
        # )

        self._chat.temperature = 0.3

        # Create a vector context aware chat retriever
        rephrase_prompt_template = ChatPromptTemplate.from_template(REPHRASE_PROMPT)
        rephrase_chain = rephrase_prompt_template | self._chat
        #
        # Rephrase the question
        rephrased_question = await rephrase_chain.ainvoke({"chat_history": messages[:-1], "question": messages[-1]})

        print(rephrased_question.content)
        # Perform vector search
        # vector_context = await retriever.ainvoke(str(rephrased_question.content))
        # data_points: list[DataPoint] = get_data_points(vector_context)

        # Create a vector context aware chat retriever
        context_prompt_template = ChatPromptTemplate.from_template(CONTEXT_PROMPT)
        self._chat.temperature = temperature
        context_chain = context_prompt_template | self._chat
        # documents_list: list[Document] = []

        # if data_points:
        #     # Perform RAG search
        #     response = context_chain.astream(
        #         {"context": [dp.to_dict() for dp in data_points], "input": rephrased_question.content}
        #     )
        #     for document in vector_context:
        #         documents_list.append(
        #             Document(page_content=document.page_content, metadata={"source": document.metadata["source"]})
        #         )
        #     return documents_list, response

        # Perform RAG search with no context
        response = context_chain.astream({"context": [], "input": rephrased_question.content})
        return [], response
