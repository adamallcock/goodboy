import type { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "primary" | "ghost" | "danger";
  children: ReactNode;
}

export function Button({ variant = "default", className = "", children, ...props }: ButtonProps) {
  const variantClass = variant === "default" ? "" : variant;
  return (
    <button className={`button ${variantClass} ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}
