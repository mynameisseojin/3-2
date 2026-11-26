from fastapi.middleware.cors import CORSMiddleware
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from datetime import date, datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from firebase_db import db

app = FastAPI(title="나만의 판매 데이터 AI 비서")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://3-2-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SalesRecord(BaseModel):
    date: date
    item: str = Field(min_length=1, max_length=50)
    value: int | None = Field(default=None, ge=0)
    memo: str = Field(default="", max_length=300)


def record_to_dict(record: SalesRecord) -> dict:
    data = record.model_dump()
    data["date"] = record.date.isoformat()
    return data


@app.get("/")
def home():
    return {"message": "판매 데이터 AI 비서 API가 실행 중입니다."}


@app.post("/api/data")
def create_data(record: SalesRecord):
    record_id = str(uuid4())
    data = record_to_dict(record)

    db.collection("data").document(record_id).set(data)

    return {
        "message": "데이터를 추가했습니다.",
        "data": {"id": record_id, **data},
    }

@app.post("/api/data/bulk")
def bulk_create_data(records: list[SalesRecord]):
    if not records:
        raise HTTPException(status_code=400, detail="등록할 데이터가 없습니다.")

    if len(records) > 450:
        raise HTTPException(
            status_code=400,
            detail="한 번에 최대 450건까지 등록할 수 있습니다.",
        )

    batch = db.batch()
    created_records = []

    for record in records:
        record_id = str(uuid4())
        data = record_to_dict(record)
        document = db.collection("data").document(record_id)
        batch.set(document, data)
        created_records.append({"id": record_id, **data})

    batch.commit()

    return {
        "message": f"{len(created_records)}건을 추가했습니다.",
        "count": len(created_records),
        "data": created_records,
    }


@app.get("/api/data")
def get_data():
    documents = db.collection("data").stream()
    records = [{"id": doc.id, **doc.to_dict()} for doc in documents]
    return sorted(records, key=lambda record: record["date"])


@app.put("/api/data/{record_id}")
def update_data(record_id: str, updated_record: SalesRecord):
    document = db.collection("data").document(record_id)

    if not document.get().exists:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")

    data = record_to_dict(updated_record)
    document.set(data)

    return {
        "message": "데이터를 수정했습니다.",
        "data": {"id": record_id, **data},
    }


@app.delete("/api/data/{record_id}")
def delete_data(record_id: str):
    document = db.collection("data").document(record_id)

    if not document.get().exists:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")

    deleted_data = document.get().to_dict()
    document.delete()

    return {
        "message": "데이터를 삭제했습니다.",
        "data": {"id": record_id, **deleted_data},
    }


@app.get("/api/data/summary")
def get_summary():
    documents = db.collection("data").stream()
    records = [
        {"id": doc.id, **doc.to_dict()}
        for doc in documents
    ]

    valid_records = [
        record for record in records
        if record.get("value") is not None
    ]

    if not valid_records:
        return {
            "count": 0,
            "period": None,
            "by_item": {},
            "message": "판매 데이터가 아직 없습니다.",
        }

    dates = [date.fromisoformat(record["date"]) for record in valid_records]
    by_item = {}

    for item in sorted({record["item"] for record in valid_records}):
        values = [
            record["value"]
            for record in valid_records
            if record["item"] == item
        ]

        by_item[item] = {
            "count": len(values),
            "total": sum(values),
            "average": round(sum(values) / len(values), 2),
            "max": max(values),
            "min": min(values),
        }

    return {
        "count": len(valid_records),
        "period": f"{min(dates)} ~ {max(dates)}",
        "by_item": by_item,
    }
class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=5000)


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=80)
    messages: list[ConversationMessage] = Field(min_length=1)


@app.post("/api/conversations")
def create_conversation(conversation: ConversationCreate):
    conversation_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    messages = [
        message.model_dump()
        for message in conversation.messages
    ]

    title = conversation.title
    if not title:
        first_user_message = next(
            (
                message["content"]
                for message in messages
                if message["role"] == "user"
            ),
            "새 대화",
        )
        title = first_user_message[:40]

    data = {
        "title": title,
        "messages": messages,
        "created_at": now,
        "updated_at": now,
    }

    db.collection("conversations").document(conversation_id).set(data)

    return {
        "message": "대화를 저장했습니다.",
        "id": conversation_id,
        **data,
    }


@app.get("/api/conversations")
def get_conversations():
    documents = db.collection("conversations").stream()

    conversations = []
    for document in documents:
        data = document.to_dict()
        conversations.append({
            "id": document.id,
            "title": data.get("title", "새 대화"),
            "updated_at": data.get("updated_at"),
            "message_count": len(data.get("messages", [])),
        })

    return sorted(
        conversations,
        key=lambda conversation: conversation["updated_at"] or "",
        reverse=True,
    )


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    document = db.collection("conversations").document(conversation_id).get()

    if not document.exists:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")

    return {"id": document.id, **document.to_dict()}


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    document = db.collection("conversations").document(conversation_id)

    if not document.get().exists:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")

    document.delete()
    return {"message": "대화를 삭제했습니다.", "id": conversation_id}
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


@app.post("/api/chat")
def chat(request: ChatRequest):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY가 설정되지 않았습니다.",
        )

    # Firestore에서 저장된 판매 요약과 기록을 읽음
        # Firestore에서 통계 요약과 상세 판매 기록을 읽음
    summary = get_summary()
    records = get_data()

    # 통계표: 집계된 숫자의 의미를 열마다 명확히 표시
    summary_rows = [
        "| 상품명 | 기록 건수(count, 건) | 총 판매량(total, 개) | 평균(개/기록) | 최대(개) | 최소(개) |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for item, stats in sorted(summary.get("by_item", {}).items()):
        summary_rows.append(
            f"| {item} "
            f"| {stats['count']} "
            f"| {stats['total']} "
            f"| {stats['average']} "
            f"| {stats['max']} "
            f"| {stats['min']} |"
        )

    summary_table = "\n".join(summary_rows)

    # 상세표: 한 행이 날짜별 상품 판매 기록 한 건
    record_rows = [
        "| 날짜 | 상품명 | 판매량(value, 개) | 메모 |",
        "|---|---|---:|---|",
    ]

    for record in sorted(records, key=lambda row: (row["date"], row["item"])):
        if record.get("value") is None:
            continue

        item = str(record["item"]).replace("|", "/")
        memo = str(record.get("memo", "")).replace("|", "/").replace("\n", " ")
        record_rows.append(
            f"| {record['date']} | {item} | {record['value']} | {memo} |"
        )

    records_table = "\n".join(record_rows)

    system_prompt = f"""
너는 사용자의 상품별 판매 데이터를 분석하는 비서야.
한국어로 답하고, 아래 표에 있는 값만 근거로 사용해.

[데이터 요약]
기간: {summary.get("period")}
전체 기록 건수: {summary.get("count")}건

{summary_table}

[날짜별 상세 기록]
{records_table}

[열 해석 규칙 — 반드시 지켜]
1. '기록 건수(count, 건)'는 저장된 판매 기록의 수다. 판매된 상품 개수가 아니다.
2. '총 판매량(total, 개)'은 해당 상품의 판매 개수 합계다.
3. count와 total은 서로 다른 열이다. 두 숫자를 붙이거나 섞지 마.
4. 상품명은 표의 행과 정확히 일치시켜. '소'와 '대' 상품의 통계를 서로 바꾸지 마.
5. 상품별 합계·평균·최대·최소를 물으면 [데이터 요약] 표의 해당 상품 행을 그대로 사용해.
6. 특정 날짜의 판매량을 물으면 [날짜별 상세 기록]에서 날짜와 상품명이 모두 일치하는 행을 찾아.
7. 메모에 '과제용 보충 데이터(실제 기록 아님)'라고 쓰인 행은 실제 판매 기록이 아닌 보충 데이터라고 밝혀.
8. 필요한 값이 표에 없으면 추측하지 말고 확인할 수 없다고 말해.
9. 답변에는 단위를 명시해. 예: '기록 18건, 총 779개 판매'.
"""


    if request.conversation_id:
        conversation_id = request.conversation_id
        document = db.collection("conversations").document(conversation_id).get()

        if not document.exists:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")

        conversation = document.to_dict()
        messages = conversation.get("messages", [])
        title = conversation.get("title", "새 대화")
        created_at = conversation.get("created_at")
    else:
        conversation_id = str(uuid4())
        messages = []
        title = request.message[:40]
        created_at = datetime.now(timezone.utc).isoformat()

    messages.append({
        "role": "user",
        "content": request.message,
    })

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                *messages,
            ],
            max_tokens=400,
        )
        answer = response.choices[0].message.content or "답변을 생성하지 못했습니다."
    except Exception as e:
        print("OpenAI 오류:", type(e).__name__, str(e))
        raise HTTPException(
            status_code=502,
            detail="GPT 응답 요청에 실패했습니다. 터미널 로그를 확인해 주세요.",
        )


    messages.append({
        "role": "assistant",
        "content": answer,
    })

    now = datetime.now(timezone.utc).isoformat()
    db.collection("conversations").document(conversation_id).set({
        "title": title,
        "messages": messages,
        "created_at": created_at or now,
        "updated_at": now,
    })

    return {
        "conversation_id": conversation_id,
        "answer": answer,
        "messages": messages,
    }
