import { Card, ChoiceGroup } from "../../shared/ui";

/** Một câu hỏi trắc nghiệm một đáp án. Không biết gì về API: nhận câu hỏi, giá trị đang chọn và hàm onChange. */
export default function QuestionCard({ index, question, value, onChange, disabled }) {
  return (
    <Card>
      <p>
        <strong>Câu {index + 1}.</strong> {question.content}
      </p>
      <ChoiceGroup
        name={`question-${question.id}`}
        options={question.choices.map((c) => ({ value: c.id, label: c.text }))}
        value={value}
        onChange={(choiceId) => onChange(question.id, choiceId)}
        disabled={disabled}
      />
    </Card>
  );
}
