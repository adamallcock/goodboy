import type { ActivityItem } from "../../lib/types";

interface ActivityDrawerProps {
  open: boolean;
  activities: ActivityItem[];
}

export function ActivityDrawer({ open, activities }: ActivityDrawerProps) {
  return (
    <aside className={`activity-drawer ${open ? "open" : ""}`} aria-label="Activity drawer">
      <div className="activity-list">
        {activities.slice(0, 5).map((item) => (
          <div className="activity-row" key={item.id}>
            <span>{item.time}</span>
            <strong>{item.label}</strong>
            <span>{item.detail}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
