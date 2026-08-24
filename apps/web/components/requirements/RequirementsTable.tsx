"use client";

import { useMemo, useState } from "react";
import type { ArtifactType } from "@rdc/domain";
import { ARTIFACT_TYPE_LABEL, statusPill, type RegisterRow } from "@/lib/workspaces";

type SortKey = "title" | "statement" | "type" | "workspace" | "source" | "status" | "confidence";
type SortDirection = "asc" | "desc";

interface RequirementsTableProps {
  rows: RegisterRow[];
  isLoading: boolean;
  onOpenSession: (sessionId: string) => void;
  getWorkspaceName?: (sessionId: string) => string;
}

function SortHeader({
  label,
  sortKey,
  activeKey,
  direction,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  direction: SortDirection;
  onSort: (key: SortKey) => void;
}) {
  const active = sortKey === activeKey;
  return (
    <th aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" className="sort-button" onClick={() => onSort(sortKey)}>
        {label}
        <span aria-hidden="true">{active ? (direction === "asc" ? "↑" : "↓") : "↕"}</span>
      </button>
    </th>
  );
}

export function RequirementsTable({
  rows,
  isLoading,
  onOpenSession,
  getWorkspaceName,
}: RequirementsTableProps) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<ArtifactType | "all">("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("confidence");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const typeOptions = useMemo(
    () =>
      Array.from(new Set(rows.map((row) => row.artifact.artifact_type))).sort((a, b) =>
        ARTIFACT_TYPE_LABEL[a].localeCompare(ARTIFACT_TYPE_LABEL[b]),
      ),
    [rows],
  );
  const statusOptions = useMemo(
    () =>
      Array.from(new Set(rows.map((row) => row.artifact.status))).sort((a, b) =>
        statusPill(a).label.localeCompare(statusPill(b).label),
      ),
    [rows],
  );

  const visibleRows = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    const filtered = rows.filter((row) => {
      const workspaceName = getWorkspaceName?.(row.sessionId) ?? "";
      const matchesSearch =
        !query ||
        [
          row.artifact.title,
          row.artifact.statement,
          ARTIFACT_TYPE_LABEL[row.artifact.artifact_type],
          statusPill(row.artifact.status).label,
          row.sessionTitle,
          workspaceName,
        ].some((value) => value.toLocaleLowerCase().includes(query));
      return (
        matchesSearch &&
        (typeFilter === "all" || row.artifact.artifact_type === typeFilter) &&
        (statusFilter === "all" || row.artifact.status === statusFilter)
      );
    });

    const valueFor = (row: RegisterRow): string | number => {
      switch (sortKey) {
        case "title":
          return row.artifact.title;
        case "statement":
          return row.artifact.statement;
        case "type":
          return ARTIFACT_TYPE_LABEL[row.artifact.artifact_type];
        case "workspace":
          return getWorkspaceName?.(row.sessionId) ?? "";
        case "source":
          return row.sessionTitle;
        case "status":
          return statusPill(row.artifact.status).label;
        case "confidence":
          return row.artifact.confidence;
      }
    };

    return filtered.sort((left, right) => {
      const leftValue = valueFor(left);
      const rightValue = valueFor(right);
      const comparison =
        typeof leftValue === "number" && typeof rightValue === "number"
          ? leftValue - rightValue
          : String(leftValue).localeCompare(String(rightValue));
      if (comparison !== 0) return sortDirection === "asc" ? comparison : -comparison;
      return left.artifact.title.localeCompare(right.artifact.title);
    });
  }, [getWorkspaceName, rows, search, sortDirection, sortKey, statusFilter, typeFilter]);

  function sortBy(key: SortKey) {
    if (key === sortKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDirection(key === "confidence" ? "desc" : "asc");
  }

  const filtered = Boolean(search.trim() || typeFilter !== "all" || statusFilter !== "all");

  return (
    <>
      <div className="requirements-controls">
        <div className="requirements-control-row">
          <label className="requirements-search">
            <span>Search</span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Title, requirement, source…"
            />
          </label>
          <label className="requirements-select">
            <span>Status</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="all">All statuses</option>
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {statusPill(status).label}
                </option>
              ))}
            </select>
          </label>
          <span className="requirements-count" aria-live="polite">
            {visibleRows.length} of {rows.length}
          </span>
          {filtered ? (
            <button
              type="button"
              className="btn clear-requirements"
              onClick={() => {
                setSearch("");
                setTypeFilter("all");
                setStatusFilter("all");
              }}
            >
              Clear filters
            </button>
          ) : null}
        </div>
        <div className="reg-chips" aria-label="Artifact type filter">
          <button
            type="button"
            className={`reg-chip${typeFilter === "all" ? " active" : ""}`}
            onClick={() => setTypeFilter("all")}
          >
            All types
          </button>
          {typeOptions.map((type) => (
            <button
              type="button"
              key={type}
              className={`reg-chip${typeFilter === type ? " active" : ""}`}
              onClick={() => setTypeFilter(type)}
            >
              {ARTIFACT_TYPE_LABEL[type]}
            </button>
          ))}
        </div>
      </div>

      <div className="reg-wrap">
        <table className="register database-requirements">
          <thead>
            <tr>
              <SortHeader
                label="Title"
                sortKey="title"
                activeKey={sortKey}
                direction={sortDirection}
                onSort={sortBy}
              />
              <SortHeader
                label="Requirement / artifact"
                sortKey="statement"
                activeKey={sortKey}
                direction={sortDirection}
                onSort={sortBy}
              />
              <SortHeader
                label="Type"
                sortKey="type"
                activeKey={sortKey}
                direction={sortDirection}
                onSort={sortBy}
              />
              {getWorkspaceName ? (
                <SortHeader
                  label="Workspace"
                  sortKey="workspace"
                  activeKey={sortKey}
                  direction={sortDirection}
                  onSort={sortBy}
                />
              ) : null}
              <SortHeader
                label="Source conversation"
                sortKey="source"
                activeKey={sortKey}
                direction={sortDirection}
                onSort={sortBy}
              />
              <SortHeader
                label="Status"
                sortKey="status"
                activeKey={sortKey}
                direction={sortDirection}
                onSort={sortBy}
              />
              <SortHeader
                label="Conf."
                sortKey="confidence"
                activeKey={sortKey}
                direction={sortDirection}
                onSort={sortBy}
              />
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => {
              const pill = statusPill(row.artifact.status);
              return (
                <tr key={row.artifact.id} onClick={() => onOpenSession(row.sessionId)}>
                  <td className="rid">{row.artifact.title}</td>
                  <td className="ritem">{row.artifact.statement}</td>
                  <td>
                    <span className="rcell-type">
                      <i className={`type-dot ${row.artifact.artifact_type}`} />
                      {ARTIFACT_TYPE_LABEL[row.artifact.artifact_type]}
                    </span>
                  </td>
                  {getWorkspaceName ? (
                    <td className="rsource">{getWorkspaceName(row.sessionId)}</td>
                  ) : null}
                  <td className="rsource">{row.sessionTitle}</td>
                  <td>
                    <span className={`reg-pill ${pill.cls}`}>{pill.label}</span>
                  </td>
                  <td>{Math.round(row.artifact.confidence * 100)}%</td>
                </tr>
              );
            })}
            {!isLoading && visibleRows.length === 0 ? (
              <tr>
                <td colSpan={getWorkspaceName ? 7 : 6} className="table-empty">
                  {rows.length === 0
                    ? "No requirements or discovery artifacts yet."
                    : "No requirements match these filters."}
                </td>
              </tr>
            ) : null}
            {isLoading && rows.length === 0 ? (
              <tr>
                <td colSpan={getWorkspaceName ? 7 : 6} className="table-empty">
                  Loading requirements…
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </>
  );
}
