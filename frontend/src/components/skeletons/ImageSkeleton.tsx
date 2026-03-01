// ImageSkeleton — Loading placeholder for images
// Soviet-themed pulsing placeholder

import { Skeleton } from "@/components/ui/skeleton";

interface ImageSkeletonProps {
  className?: string;
  aspectRatio?: "square" | "video" | "wide" | "portrait";
}

const aspectClasses = {
  square: "aspect-square",
  video: "aspect-video",
  wide: "aspect-[4/3]",
  portrait: "aspect-[3/4]",
};

export function ImageSkeleton({ className = "", aspectRatio = "wide" }: ImageSkeletonProps) {
  return (
    <div className={`relative w-full overflow-hidden ${aspectClasses[aspectRatio]} ${className}`}>
      <Skeleton className="absolute inset-0 bg-soviet-red/5" />

      {/* Soviet-style loading indicator */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-soviet-red/20 text-2xl animate-pulse">
          ☭
        </div>
      </div>

      {/* Scanline effect */}
      <div
        className="absolute inset-0 pointer-events-none opacity-10"
        style={{
          background: "repeating-linear-gradient(0deg, transparent, transparent 2px, hsl(0 0% 0% / 0.1) 2px, hsl(0 0% 0% / 0.1) 4px)",
        }}
      />
    </div>
  );
}

export default ImageSkeleton;
