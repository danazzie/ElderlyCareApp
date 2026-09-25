import type { LucideIcon } from "lucide-react";
import {
  Ban, Bell, CalendarDays, Check, ChevronLeft, ChevronRight, CircleAlert,
  CircleCheck, ClipboardList, Clock, FileText, FolderOpen, House, Image,
  LogOut, Mic, Pencil, Phone, Pill, Plus, Scale, ScanLine, ScrollText, Send,
  ShieldCheck, Smile, Sparkles, Square, Stethoscope, Trash2, TriangleAlert, Upload,
  Users, Utensils, X,
} from "lucide-react";

const ICONS = {
  house: House,
  calendar: CalendarDays,
  sparkles: Sparkles,
  folder: FolderOpen,
  users: Users,
  mic: Mic,
  scan: ScanLine,
  bell: Bell,
  pill: Pill,
  stethoscope: Stethoscope,
  file: FileText,
  check: Check,
  chevronRight: ChevronRight,
  chevronLeft: ChevronLeft,
  alert: TriangleAlert,
  circleAlert: CircleAlert,
  plus: Plus,
  utensils: Utensils,
  smile: Smile,
  send: Send,
  clipboard: ClipboardList,
  phone: Phone,
  image: Image,
  pencil: Pencil,
  close: X,
  shield: ShieldCheck,
  clock: Clock,
  circleCheck: CircleCheck,
  ban: Ban,
  scroll: ScrollText,
  upload: Upload,
  scale: Scale,
  stop: Square,
  logOut: LogOut,
  trash: Trash2,
} as const;

export type IconName = keyof typeof ICONS;

export function Icon({
  name, size = 20, stroke = 1.75, className,
}: { name: IconName; size?: number; stroke?: number; className?: string }) {
  const C: LucideIcon = ICONS[name];
  return <C size={size} strokeWidth={stroke} className={className} aria-hidden />;
}

export function IconTile({
  name, tone = "green", size = 36, iconSize = 18,
}: { name: IconName; tone?: "green" | "coral" | "amber" | "ink"; size?: number; iconSize?: number }) {
  return (
    <span className={`icon-tile ${tone}`} style={{ width: size, height: size }}>
      <Icon name={name} size={iconSize} />
    </span>
  );
}
