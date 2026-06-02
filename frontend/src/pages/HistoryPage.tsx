import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Title,
  TextInput,
  Button,
  Group,
  Table,
  Modal,
  Stack,
  Text,
  Box,
  Badge,
  Divider,
  Paper,
} from "@mantine/core";
import {
  listSales,
  getReceipt,
  type Receipt,
} from "../api/client";

function ReceiptView({ receipt }: { receipt: Receipt }) {
  return (
    <Stack gap="sm">
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Date</Text>
        <Text size="sm">{new Date(receipt.created_at).toLocaleString()}</Text>
      </Group>
      {receipt.customer_name && (
        <Group justify="space-between">
          <Text size="sm" c="dimmed">Customer</Text>
          <Text size="sm">{receipt.customer_name}</Text>
        </Group>
      )}

      <Divider />

      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Product</Table.Th>
            <Table.Th>Qty</Table.Th>
            <Table.Th>Unit price</Table.Th>
            <Table.Th>Total</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {receipt.items.map((item, i) => (
            <Table.Tr key={i}>
              <Table.Td>{item.product_name}</Table.Td>
              <Table.Td>{item.qty}</Table.Td>
              <Table.Td>{item.unit_price.toFixed(2)}</Table.Td>
              <Table.Td>{item.line_total.toFixed(2)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Divider />

      <Group justify="space-between">
        <Text size="sm" c="dimmed">Subtotal</Text>
        <Text size="sm">{receipt.subtotal.toFixed(2)}</Text>
      </Group>
      {receipt.discount_pct > 0 && (
        <Group justify="space-between">
          <Text size="sm" c="dimmed">Discount ({receipt.discount_pct}%)</Text>
          <Text size="sm" c="red">-{receipt.discount_amount.toFixed(2)}</Text>
        </Group>
      )}
      <Group justify="space-between">
        <Text fw={700}>TOTAL</Text>
        <Text fw={700}>{receipt.total.toFixed(2)}</Text>
      </Group>

      <Group justify="center" mt="xs">
        <Badge
          color={receipt.payment_status === "paid" ? "green" : "red"}
          size="lg"
        >
          {receipt.payment_status.toUpperCase()}
        </Badge>
      </Group>
    </Stack>
  );
}

export default function HistoryPage() {
  const [search, setSearch] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data: sales = [], isLoading } = useQuery({
    queryKey: ["sales", search, start, end],
    queryFn: () => listSales({ search, start, end }),
  });

  const { data: receipt } = useQuery({
    queryKey: ["receipt", selectedId],
    queryFn: () => getReceipt(selectedId!),
    enabled: selectedId !== null,
  });

  const totalRevenue = sales.reduce((sum, s) => sum + s.total, 0);

  function handleClear() {
    setSearch("");
    setStart("");
    setEnd("");
  }

  return (
    <Box>
      <Title order={3} mb="md">Sales History</Title>

      {/* Filters */}
      <Paper withBorder p="md" radius="sm" mb="md">
        <Group align="flex-end" gap="sm" wrap="wrap">
          <TextInput
            label="Search"
            placeholder="product or customer"
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            style={{ flex: 1, minWidth: 160 }}
          />
          <TextInput
            label="From"
            type="date"
            value={start}
            onChange={(e) => setStart(e.currentTarget.value)}
            style={{ width: 160 }}
          />
          <TextInput
            label="To"
            type="date"
            value={end}
            onChange={(e) => setEnd(e.currentTarget.value)}
            style={{ width: 160 }}
          />
          <Button variant="light" onClick={handleClear}>
            Clear
          </Button>
        </Group>
      </Paper>

      {/* Summary */}
      <Group justify="flex-end" mb="xs">
        <Text size="sm" c="dimmed">Total revenue:</Text>
        <Text fw={600}>{totalRevenue.toFixed(2)}</Text>
      </Group>

      {/* Table */}
      <Paper withBorder radius="sm">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>#</Table.Th>
              <Table.Th>Date</Table.Th>
              <Table.Th>Customer</Table.Th>
              <Table.Th>Items</Table.Th>
              <Table.Th>Total</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text c="dimmed" size="sm">Loading…</Text>
                </Table.Td>
              </Table.Tr>
            )}
            {!isLoading && sales.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text c="dimmed" size="sm">No sales found.</Text>
                </Table.Td>
              </Table.Tr>
            )}
            {sales.map((sale) => (
              <Table.Tr
                key={sale.id}
                style={{ cursor: "pointer" }}
                onClick={() => setSelectedId(sale.id)}
              >
                <Table.Td>{sale.id}</Table.Td>
                <Table.Td>{new Date(sale.created_at).toLocaleString()}</Table.Td>
                <Table.Td>{sale.customer_name ?? "—"}</Table.Td>
                <Table.Td>{sale.item_count}</Table.Td>
                <Table.Td>{sale.total.toFixed(2)}</Table.Td>
                <Table.Td>
                  <Badge color={sale.payment_status === "paid" ? "green" : "red"} size="sm">
                    {sale.payment_status}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      {/* Receipt Modal */}
      <Modal
        opened={selectedId !== null}
        onClose={() => setSelectedId(null)}
        title={`Receipt #${selectedId}`}
        size="md"
      >
        {receipt ? (
          <Stack gap="sm">
            <ReceiptView receipt={receipt} />
            <Button fullWidth mt="sm" onClick={() => setSelectedId(null)}>
              Close
            </Button>
          </Stack>
        ) : (
          <Text c="dimmed" size="sm">Loading receipt…</Text>
        )}
      </Modal>
    </Box>
  );
}
