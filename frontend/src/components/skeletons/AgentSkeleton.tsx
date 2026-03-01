// AgentSkeleton — Loading placeholder for agent cards
// Matches the layout of agent cards in SwarmPanel

import { Skeleton } from "@/components/ui/skeleton";

export function AgentSkeleton() {
  return (
    <div className="bg-card/30 border border-border/30 p-3 rounded">
      {/* Header: avatar + name */}
      <div className="flex items-center gap-2 mb-3">
        <Skeleton className="w-8 h-8 rounded-full bg-soviet-red/10" />
        <Skeleton className="h-4 w-24 bg-secondary/20" />
      </div>

      {/* Stats bars */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Skeleton className="h-2 w-12 bg-secondary/10" />
          <Skeleton className="h-2 flex-1 bg-secondary/15" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-2 w-12 bg-secondary/10" />
          <Skeleton className="h-2 flex-1 bg-secondary/15" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-2 w-12 bg-secondary/10" />
          <Skeleton className="h-2 flex-1 bg-secondary/15" />
        </div>
      </div>

      {/* Status line */}
      <div className="mt-3 pt-2 border-t border-border/20">
        <Skeleton className="h-3 w-32 bg-soviet-red/10" />
      </div>
    </div>
  );
}

export function AgentSkeletonGrid() {
  return (
    <div className="grid grid-cols-2 gap-3">
      <AgentSkeleton />
      <AgentSkeleton />
      <AgentSkeleton />
      <AgentSkeleton />
    </div>
  );
}

export default AgentSkeleton;
