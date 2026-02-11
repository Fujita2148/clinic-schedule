"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "シフト表" },
  { href: "/staffs", label: "職員管理" },
  { href: "/task-types", label: "業務コード管理" },
  { href: "/events", label: "イベント管理" },
  { href: "/rules", label: "ルール管理" },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav className="bg-gray-800 text-white px-4 py-2 flex items-center gap-6">
      <span className="font-bold text-sm">クリニック スケジュール</span>
      <div className="flex gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`px-3 py-1.5 rounded text-sm transition-colors ${
                isActive
                  ? "bg-gray-600 text-white"
                  : "text-gray-300 hover:bg-gray-700 hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
