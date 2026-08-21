import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Title,
  Text,
  Select,
  TextInput,
  Button,
  Group,
  Paper,
  Table,
  Stack,
  Box,
  Badge,
  SimpleGrid,
  Accordion,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  getReport,
  downloadReportExcel,
  type ReportParams,
} from "../api/client";

const TYPE_OPTIONS = [
  { value: "Daily", label: "Daily" },
  { value: "Weekly", label: "Weekly" },
  { value: "Monthly", label: "Monthly" },
  { value: "Yearly", label: "Yearly" },
  { value: "Custom", label: "Custom Range" },
];

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Paper withBorder p="md" radius="sm">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={4}>
        {label}
      </Text>
      <Text size="xl" fw={700}>
        {value}
      </Text>
    </Paper>
  );
}

function EmptyRow({ cols }: { cols: number }) {
  return (
    <Table.Tr>
      <Table.Td colSpan={cols}>
        <Text c="dimmed" size="sm" ta="center">
          None
        </Text>
      </Table.Td>
    </Table.Tr>
  );
}

export default function ReportsPage() {
  const [reportType, setReportType] = useState<string>("Daily");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [appliedParams, setAppliedParams] = useState<ReportParams | null>(null);
  const [exporting, setExporting] = useState(false);

  const isCustom = reportType === "Custom";

  const { data: report, isFetching, error } = useQuery({
    queryKey: ["report", appliedParams],
    queryFn: () => getReport(appliedParams!),
    enabled: appliedParams !== null,
  });

  function buildParams(): ReportParams {
    if (isCustom) {
      return { start: start || undefined, end: end || undefined };
    }
    return { type: reportType };
  }

  function handleGenerate() {
    setAppliedParams(buildParams());
  }

  async function handleExport() {
    if (!appliedParams) return;
    setExporting(true);
    try {
      const blob = await downloadReportExcel(appliedParams);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "sante-report.xlsx";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      notifications.show({
        title: "Export successful",
        message: "sante-report.xlsx downloaded.",
        color: "green",
      });
    } catch (err) {
      notifications.show({
        title: "Export failed",
        message: err instanceof Error ? err.message : "Unknown error",
        color: "red",
      });
    } finally {
      setExporting(false);
    }
  }

  return (
    <Box>
      <Title order={3} mb="md">
        Reports
      </Title>

      {/* Controls */}
      <Paper withBorder p="md" radius="sm" mb="md">
        <Group align="flex-end" gap="sm" wrap="wrap">
          <Select
            label="Report Type"
            data={TYPE_OPTIONS}
            value={reportType}
            onChange={(v) => setReportType(v ?? "Daily")}
            style={{ width: 180 }}
          />
          {isCustom && (
            <>
              <TextInput
                label="Start Date"
                type="date"
                value={start}
                onChange={(e) => setStart(e.currentTarget.value)}
                style={{ width: 160 }}
              />
              <TextInput
                label="End Date"
                type="date"
                value={end}
                onChange={(e) => setEnd(e.currentTarget.value)}
                style={{ width: 160 }}
              />
            </>
          )}
          <Button onClick={handleGenerate} loading={isFetching}>
            Generate
          </Button>
          <Button
            variant="light"
            color="teal"
            onClick={handleExport}
            loading={exporting}
            disabled={appliedParams === null}
          >
            Export Excel
          </Button>
        </Group>
      </Paper>

      {/* Error */}
      {error && (
        <Text c="red" mb="md">
          {error instanceof Error ? error.message : "Failed to load report."}
        </Text>
      )}

      {/* Report content */}
      {report && (
        <Stack gap="lg">
          {/* Range label */}
          <Text size="sm" c="dimmed">
            Period: <strong>{report.range.label}</strong> ({report.range.start}{" "}
            → {report.range.end})
          </Text>

          {/* Overview cards */}
          <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="sm">
            <StatCard
              label="Sales Count"
              value={String(report.overview.sales_count)}
            />
            <StatCard
              label="Paid Revenue"
              value={report.overview.paid_revenue.toFixed(2)}
            />
            <StatCard
              label="Unpaid Debt"
              value={report.overview.unpaid_debt.toFixed(2)}
            />
            <StatCard
              label="Grand Total"
              value={report.overview.grand_total.toFixed(2)}
            />
          </SimpleGrid>

          {/* Detail sections in Accordion */}
          <Accordion multiple defaultValue={["sales_details"]}>
            {/* Sales Details */}
            <Accordion.Item value="sales_details">
              <Accordion.Control>
                <Text fw={600}>Sales Details ({report.sales_details.length})</Text>
              </Accordion.Control>
              <Accordion.Panel>
                <Paper withBorder radius="sm">
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>#</Table.Th>
                        <Table.Th>Date</Table.Th>
                        <Table.Th>Product</Table.Th>
                        <Table.Th>Qty</Table.Th>
                        <Table.Th>Line Total</Table.Th>
                        <Table.Th>Customer</Table.Th>
                        <Table.Th>Status</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {report.sales_details.length === 0 ? (
                        <EmptyRow cols={7} />
                      ) : (
                        report.sales_details.map((row, i) => (
                          <Table.Tr key={i}>
                            <Table.Td>{row.sale_id}</Table.Td>
                            <Table.Td>
                              {new Date(row.date).toLocaleDateString()}
                            </Table.Td>
                            <Table.Td>{row.product}</Table.Td>
                            <Table.Td>{row.qty}</Table.Td>
                            <Table.Td>{row.line_total.toFixed(2)}</Table.Td>
                            <Table.Td>{row.customer ?? "—"}</Table.Td>
                            <Table.Td>
                              <Badge
                                color={
                                  row.payment_status === "paid" ? "green" : "red"
                                }
                                size="sm"
                              >
                                {row.payment_status}
                              </Badge>
                            </Table.Td>
                          </Table.Tr>
                        ))
                      )}
                    </Table.Tbody>
                  </Table>
                </Paper>
              </Accordion.Panel>
            </Accordion.Item>

            {/* Inventory Consumption */}
            <Accordion.Item value="inventory_consumption">
              <Accordion.Control>
                <Text fw={600}>
                  Inventory Consumption ({report.inventory_consumption.length})
                </Text>
              </Accordion.Control>
              <Accordion.Panel>
                <Paper withBorder radius="sm">
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Ingredient</Table.Th>
                        <Table.Th>Consumed</Table.Th>
                        <Table.Th>Remaining</Table.Th>
                        <Table.Th>Unit</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {report.inventory_consumption.length === 0 ? (
                        <EmptyRow cols={4} />
                      ) : (
                        report.inventory_consumption.map((row, i) => (
                          <Table.Tr key={i}>
                            <Table.Td>{row.ingredient}</Table.Td>
                            <Table.Td>{row.consumed}</Table.Td>
                            <Table.Td>{row.remaining}</Table.Td>
                            <Table.Td>{row.unit}</Table.Td>
                          </Table.Tr>
                        ))
                      )}
                    </Table.Tbody>
                  </Table>
                </Paper>
              </Accordion.Panel>
            </Accordion.Item>

            {/* Current Inventory */}
            <Accordion.Item value="current_inventory">
              <Accordion.Control>
                <Text fw={600}>
                  Current Inventory ({report.current_inventory.length})
                </Text>
              </Accordion.Control>
              <Accordion.Panel>
                <Paper withBorder radius="sm">
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Item</Table.Th>
                        <Table.Th>Qty</Table.Th>
                        <Table.Th>Unit</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {report.current_inventory.length === 0 ? (
                        <EmptyRow cols={3} />
                      ) : (
                        report.current_inventory.map((row, i) => (
                          <Table.Tr key={i}>
                            <Table.Td>{row.name}</Table.Td>
                            <Table.Td>{row.qty}</Table.Td>
                            <Table.Td>{row.unit}</Table.Td>
                          </Table.Tr>
                        ))
                      )}
                    </Table.Tbody>
                  </Table>
                </Paper>
              </Accordion.Panel>
            </Accordion.Item>

            {/* Customer Summary */}
            <Accordion.Item value="customer_summary">
              <Accordion.Control>
                <Text fw={600}>
                  Customer Summary ({report.customer_summary.length})
                </Text>
              </Accordion.Control>
              <Accordion.Panel>
                <Paper withBorder radius="sm">
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Customer</Table.Th>
                        <Table.Th>Purchases</Table.Th>
                        <Table.Th>Paid</Table.Th>
                        <Table.Th>Debt</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {report.customer_summary.length === 0 ? (
                        <EmptyRow cols={4} />
                      ) : (
                        report.customer_summary.map((row, i) => (
                          <Table.Tr key={i}>
                            <Table.Td>{row.customer}</Table.Td>
                            <Table.Td>{row.purchases}</Table.Td>
                            <Table.Td>{row.paid.toFixed(2)}</Table.Td>
                            <Table.Td>{row.debt.toFixed(2)}</Table.Td>
                          </Table.Tr>
                        ))
                      )}
                    </Table.Tbody>
                  </Table>
                </Paper>
              </Accordion.Panel>
            </Accordion.Item>

            {/* Unpaid Bills */}
            <Accordion.Item value="unpaid_bills">
              <Accordion.Control>
                <Text fw={600}>
                  Unpaid Bills ({report.unpaid_bills.length})
                </Text>
              </Accordion.Control>
              <Accordion.Panel>
                <Paper withBorder radius="sm">
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Sale ID</Table.Th>
                        <Table.Th>Date</Table.Th>
                        <Table.Th>Customer</Table.Th>
                        <Table.Th>Total</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {report.unpaid_bills.length === 0 ? (
                        <EmptyRow cols={4} />
                      ) : (
                        report.unpaid_bills.map((row, i) => (
                          <Table.Tr key={i}>
                            <Table.Td>{row.sale_id}</Table.Td>
                            <Table.Td>
                              {new Date(row.date).toLocaleDateString()}
                            </Table.Td>
                            <Table.Td>{row.customer ?? "—"}</Table.Td>
                            <Table.Td>{row.total.toFixed(2)}</Table.Td>
                          </Table.Tr>
                        ))
                      )}
                    </Table.Tbody>
                  </Table>
                </Paper>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        </Stack>
      )}

      {/* Idle state */}
      {!report && !isFetching && !error && (
        <Text c="dimmed" mt="xl" ta="center">
          Select a report type and click Generate to view the report.
        </Text>
      )}
    </Box>
  );
}
