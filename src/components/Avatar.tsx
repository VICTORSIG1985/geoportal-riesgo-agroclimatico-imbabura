"use client";
import { useState } from "react";

export default function Avatar({ src, name, size = 80 }: { src: string; name: string; size?: number }) {
  const [err, setErr] = useState(false);
  const initials = name.split(" ").map(p => p[0]).filter(Boolean).slice(0, 3).join("");
  if (err) {
    return (
      <div
        className="rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--primary-dark)] text-white flex items-center justify-center font-bold border-4 border-white shadow"
        style={{ width: size, height: size, fontSize: Math.round(size * 0.35) }}
      >
        {initials}
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={name}
      onError={() => setErr(true)}
      className="rounded-full object-cover border-4 border-[var(--primary)] shadow"
      style={{ width: size, height: size }}
    />
  );
}
