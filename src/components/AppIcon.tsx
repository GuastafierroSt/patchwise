import {
  Archive,
  Code2,
  FileText,
  FolderGit2,
  Globe,
  Image as ImageIcon,
  MessageSquare,
  Music,
  PlaySquare,
  ShieldCheck,
  Terminal,
  Volume2,
  Wrench,
} from 'lucide-react';
import { AppIconKey } from '../core/types';

interface AppIconProps {
  icon: AppIconKey;
  className?: string;
}

export function AppIcon({ icon, className = 'w-6 h-6' }: AppIconProps) {
  switch (icon) {
    case 'browser':
      return <Globe className={className} aria-hidden="true" />;
    case 'code':
      return <Code2 className={className} aria-hidden="true" />;
    case 'music':
      return <Music className={className} aria-hidden="true" />;
    case 'video':
      return <PlaySquare className={className} aria-hidden="true" />;
    case 'archive':
      return <Archive className={className} aria-hidden="true" />;
    case 'shield':
      return <ShieldCheck className={className} aria-hidden="true" />;
    case 'chat':
      return <MessageSquare className={className} aria-hidden="true" />;
    case 'audio':
      return <Volume2 className={className} aria-hidden="true" />;
    case 'git':
      return <FolderGit2 className={className} aria-hidden="true" />;
    case 'terminal':
      return <Terminal className={className} aria-hidden="true" />;
    case 'notes':
      return <FileText className={className} aria-hidden="true" />;
    case 'image':
      return <ImageIcon className={className} aria-hidden="true" />;
    case 'tools':
      return <Wrench className={className} aria-hidden="true" />;
  }
}

export function PatchWiseLogo({ className = 'w-8 h-8' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 36 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <rect width="36" height="36" rx="10" fill="#094cb2" />
      <path
        d="M11 22.5V13.5C11 12.1193 12.1193 11 13.5 11H19.5C21.9853 11 24 13.0147 24 15.5C24 17.9853 21.9853 20 19.5 20H14.5"
        stroke="#ffffff"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M21 25L25 21M25 21L21 17M25 21H16.5"
        stroke="#f9e37a"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
