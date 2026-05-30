"use client";

import { CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import type { ComparisonTable as ComparisonTableType, CompetitorData } from "@/types";

interface ComparisonTableProps {
  table: ComparisonTableType;
  competitors: CompetitorData[];
}

export function ComparisonTable({ table, competitors }: ComparisonTableProps) {
  const nameMap = new Map<string, string>();
  for (const comp of competitors) {
    nameMap.set(comp.id, comp.name);
  }
  const getName = (id: string) => nameMap.get(id) ?? id;

  const winnerCount = table.rows.filter((r) => r.winner).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{table.title}</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto overflow-y-auto max-h-[70vh]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  Dimension
                </th>
                {table.competitor_ids.map((id) => (
                  <th
                    key={id}
                    className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-text-primary"
                  >
                    {getName(id)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, ri) => (
                <tr
                  key={ri}
                  className="border-b border-border/50 last:border-0 hover:bg-accent/5 transition-colors"
                >
                  <td className="px-5 py-3 font-medium text-text-secondary">
                    {row.dimension}
                  </td>
                  {table.competitor_ids.map((id) => {
                    const isWinner = row.winner === id;
                    return (
                      <td
                        key={id}
                        className={`px-5 py-3 max-w-xs break-words ${
                          isWinner
                            ? "text-success font-medium"
                            : "text-text-secondary"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {isWinner && (
                            <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
                          )}
                          {row.values[id] ?? "\u2014"}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
      {winnerCount > 0 && (
        <CardFooter>
          <p className="text-xs text-text-secondary">
            <span className="text-success font-medium">Green checkmarks</span>{" "}
            indicate the leading competitor for that dimension.
          </p>
        </CardFooter>
      )}
    </Card>
  );
}
