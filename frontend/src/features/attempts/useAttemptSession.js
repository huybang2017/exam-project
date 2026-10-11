import { useCallback, useEffect, useRef, useState } from "react";
import { WS_BASE } from "../../shared/api/httpClient.js";
import { tokenStore } from "../../shared/api/tokenStore.js";
import { useDebouncedCallback } from "../../shared/hooks/useDebouncedCallback.js";
import { useWebSocket } from "../../shared/hooks/useWebSocket.js";
import { attemptsApi } from "./attemptsApi.js";

const SAVE_DELAY_MS = 500;

/**
 * Toàn bộ logic một lượt làm bài, để trang chỉ còn render:
 * - bắt đầu/vào lại bài (idempotent nên F5 an toàn)
 * - chọn đáp án + tự động lưu (debounce 500 ms)
 * - đồng hồ do server đẩy qua WebSocket; hết giờ/nộp ở nơi khác thì gọi onFinished
 * - nộp bài (flush đáp án chưa lưu trước)
 */
export function useAttemptSession(examId, { onFinished }) {
  const [attempt, setAttempt] = useState(null);
  const [answers, setAnswers] = useState({}); // question_id -> choice_id
  const [remaining, setRemaining] = useState(null);
  const [saveState, setSaveState] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const pending = useRef({}); // đáp án chưa gửi lên server
  const finished = useRef(false);

  const finish = useCallback(
    (attemptId) => {
      if (finished.current) return;
      finished.current = true;
      onFinished(attemptId);
    },
    [onFinished]
  );

  // 1) Bắt đầu / vào lại bài làm
  useEffect(() => {
    let cancelled = false;
    attemptsApi.start(examId).then(
      (a) => {
        if (cancelled) return;
        if (a.submitted) return finish(a.id);
        setAttempt(a);
        setRemaining(a.remaining_seconds);
        setAnswers(Object.fromEntries(Object.entries(a.saved_answers).map(([q, c]) => [Number(q), c])));
      },
      (err) => !cancelled && setError(err)
    );
    return () => {
      cancelled = true;
    };
  }, [examId, finish]);

  // 2) Đồng hồ từ server
  const wsUrl =
    attempt && !finished.current
      ? `${WS_BASE}/ws/attempts/${attempt.id}?token=${encodeURIComponent(tokenStore.token)}`
      : null;
  useWebSocket(wsUrl, (msg) => {
    if (msg.remaining !== undefined) setRemaining(msg.remaining);
    else if (msg.event) finish(attempt.id); // expired | submitted
  });

  // 3) Tự động lưu đáp án
  const save = useCallback(async () => {
    const batch = Object.entries(pending.current).map(([q, c]) => ({ question_id: Number(q), choice_id: c }));
    if (!attempt || batch.length === 0) return;
    pending.current = {};
    setSaveState("Đang lưu...");
    try {
      await attemptsApi.saveAnswers(attempt.id, batch);
      setSaveState("Đã lưu");
    } catch (err) {
      batch.forEach((a) => (pending.current[a.question_id] ??= a.choice_id)); // thử lại lần sau
      setSaveState(`Lưu thất bại: ${err.message}`);
    }
  }, [attempt]);
  const debouncedSave = useDebouncedCallback(save, SAVE_DELAY_MS);

  const choose = useCallback(
    (questionId, choiceId) => {
      setAnswers((prev) => ({ ...prev, [questionId]: choiceId }));
      pending.current[questionId] = choiceId;
      debouncedSave.call();
    },
    [debouncedSave]
  );

  const submit = useCallback(async () => {
    setSubmitting(true);
    await debouncedSave.flush();
    try {
      await attemptsApi.submit(attempt.id);
      finish(attempt.id);
    } catch (err) {
      setError(err);
      setSubmitting(false);
    }
  }, [attempt, debouncedSave, finish]);

  return {
    questions: attempt?.questions ?? [],
    answers,
    remaining,
    saveState,
    error,
    submitting,
    ready: attempt !== null,
    choose,
    submit,
  };
}
