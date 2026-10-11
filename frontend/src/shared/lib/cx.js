/** Ghép tên class, bỏ giá trị falsy: cx("a", cond && "b") -> "a b". */
export const cx = (...parts) => parts.filter(Boolean).join(" ");
