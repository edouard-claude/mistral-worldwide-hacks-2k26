// NewsSkeleton — Loading placeholder for news cards
// Matches the layout of news cards in PropagandaPanel

import { Skeleton } from "@/components/ui/skeleton";

export function NewsSkeleton() {
  return (
    <div
      className="bg-white border-[4px] border-soviet-black/30 overflow-hidden"
      style={{ boxShadow: "4px 4px 0px hsl(var(--black) / 0.2)" }}
    >
      {/* Image placeholder — matches h-24 from NewsCard */}
      <Skeleton className="w-full h-24 bg-soviet-red/10" />

      {/* Content */}
      <div className="p-2 space-y-2">
        {/* Title */}
        <Skeleton className="h-3 w-full bg-soviet-black/15" />
        <Skeleton className="h-3 w-3/4 bg-soviet-black/10" />

        {/* Button */}
        <Skeleton className="h-7 w-full bg-soviet-red/20 mt-2" />
      </div>
    </div>
  );
}

export function NewsSkeletonGrid() {
  return (
    <div className="space-y-3">
      <NewsSkeleton />
      <NewsSkeleton />
      <NewsSkeleton />
    </div>
  );
}

export default NewsSkeleton;
