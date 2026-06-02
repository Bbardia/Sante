import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import {
  Title,
  TextInput,
  NumberInput,
  Button,
  Group,
  Table,
  Modal,
  Stack,
  ActionIcon,
  Text,
  Box,
  Grid,
  Select,
  Checkbox,
  Divider,
  Badge,
  Paper,
} from "@mantine/core";
import {
  listProducts,
  listCustomers,
  createCustomer,
  checkout,
  ApiError,
  type Receipt,
} from "../api/client";

interface CartEntry {
  product_id: number;
  name: string;
  price: number;
  qty: number;
}

interface Shortage {
  ingredient: string;
  available: number;
  needed: number;
}

export default function SalesPage() {
  const queryClient = useQueryClient();

  // ── Product selector state ──────────────────────────────────────────────────
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [addQty, setAddQty] = useState<number | string>(1);

  // ── Cart ────────────────────────────────────────────────────────────────────
  const [cart, setCart] = useState<CartEntry[]>([]);

  // ── Customer ────────────────────────────────────────────────────────────────
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [newCustomerName, setNewCustomerName] = useState("");
  const [newCustomerDiscount, setNewCustomerDiscount] = useState<number | string>(0);

  // ── Discount & Pay later ────────────────────────────────────────────────────
  const [discountPct, setDiscountPct] = useState<number | string>(0);
  const [payLater, setPayLater] = useState(false);

  // ── Receipt modal ───────────────────────────────────────────────────────────
  const [receipt, setReceipt] = useState<Receipt | null>(null);

  // ── Queries ─────────────────────────────────────────────────────────────────
  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: () => listProducts(),
  });

  const { data: customers = [] } = useQuery({
    queryKey: ["customers"],
    queryFn: () => listCustomers(),
  });

  // ── Derived ─────────────────────────────────────────────────────────────────
  const productOptions = products.map((p) => ({
    value: String(p.id),
    label: `${p.name} (${p.price.toFixed(2)})`,
  }));

  const customerOptions = customers.map((c) => ({
    value: String(c.id),
    label: `${c.name}${c.discount > 0 ? ` (${c.discount}% off)` : ""}`,
  }));

  const subtotal = cart.reduce((sum, e) => sum + e.price * e.qty, 0);
  const discount = Number(discountPct) || 0;
  const discountAmount = subtotal * (discount / 100);
  const total = subtotal - discountAmount;

  // ── Handlers ─────────────────────────────────────────────────────────────────

  function handleAddToCart() {
    if (!selectedProductId) return;
    const product = products.find((p) => String(p.id) === selectedProductId);
    if (!product) return;
    const qty = Number(addQty) || 1;
    setCart((prev) => {
      const existing = prev.find((e) => e.product_id === product.id);
      if (existing) {
        return prev.map((e) =>
          e.product_id === product.id ? { ...e, qty: e.qty + qty } : e
        );
      }
      return [...prev, { product_id: product.id, name: product.name, price: product.price, qty }];
    });
    setAddQty(1);
  }

  function handleRemoveFromCart(product_id: number) {
    setCart((prev) => prev.filter((e) => e.product_id !== product_id));
  }

  function handleCustomerChange(value: string | null) {
    setSelectedCustomerId(value);
    if (!value) {
      setPayLater(false);
    } else {
      const customer = customers.find((c) => String(c.id) === value);
      if (customer) {
        setDiscountPct(customer.discount);
      }
    }
  }

  // ── Create customer mutation ─────────────────────────────────────────────────
  const createCustomerMutation = useMutation({
    mutationFn: () =>
      createCustomer({ name: newCustomerName.trim(), discount: Number(newCustomerDiscount) || 0 }),
    onSuccess: (newCust) => {
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      setSelectedCustomerId(String(newCust.id));
      setDiscountPct(newCust.discount);
      setNewCustomerName("");
      setNewCustomerDiscount(0);
      notifications.show({ color: "green", title: "Customer added", message: `${newCust.name} created.` });
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to create customer.";
      notifications.show({ color: "red", title: "Error", message: msg });
    },
  });

  // ── Checkout mutation ────────────────────────────────────────────────────────
  const checkoutMutation = useMutation({
    mutationFn: () =>
      checkout({
        customer_id: selectedCustomerId ? Number(selectedCustomerId) : null,
        discount_pct: Number(discountPct) || 0,
        pay_later: payLater,
        items: cart.map((e) => ({ product_id: e.product_id, qty: e.qty })),
      }),
    onSuccess: (data) => {
      setReceipt(data);
      setCart([]);
      setDiscountPct(0);
      setPayLater(false);
      setSelectedCustomerId(null);
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      notifications.show({ color: "green", title: "Sale complete", message: `Receipt #${data.sale_id} created.` });
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        const detail = err.detail as { shortages?: Shortage[] } | null;
        if (detail && Array.isArray(detail.shortages) && detail.shortages.length > 0) {
          const lines = detail.shortages
            .map((s: Shortage) => `${s.ingredient}: need ${s.needed}, have ${s.available}`)
            .join("\n");
          notifications.show({
            color: "red",
            title: "Insufficient stock",
            message: lines,
            autoClose: 8000,
          });
          return;
        }
        notifications.show({ color: "red", title: "Checkout failed", message: err.message });
      } else {
        notifications.show({ color: "red", title: "Checkout failed", message: "An unexpected error occurred." });
      }
    },
  });

  return (
    <Box>
      <Title order={3} mb="md">
        Sales
      </Title>

      <Grid gap="md">
        {/* ── Left column: Product selector + Cart ── */}
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Stack gap="md">
            {/* Add to cart */}
            <Paper withBorder p="md" radius="sm">
              <Title order={5} mb="sm">
                Add to cart
              </Title>
              <Group align="flex-end" gap="sm">
                <Select
                  label="Product"
                  placeholder="Select a product"
                  data={productOptions}
                  value={selectedProductId}
                  onChange={setSelectedProductId}
                  searchable
                  style={{ flex: 1 }}
                />
                <NumberInput
                  label="Qty"
                  min={1}
                  value={addQty}
                  onChange={setAddQty}
                  style={{ width: 90 }}
                />
                <Button onClick={handleAddToCart} disabled={!selectedProductId}>
                  Add
                </Button>
              </Group>
            </Paper>

            {/* Cart table */}
            <Paper withBorder p="md" radius="sm">
              <Title order={5} mb="sm">
                Cart
              </Title>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Product</Table.Th>
                    <Table.Th>Qty</Table.Th>
                    <Table.Th>Unit price</Table.Th>
                    <Table.Th>Line total</Table.Th>
                    <Table.Th></Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {cart.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={5}>
                        <Text c="dimmed" size="sm">
                          Cart is empty.
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                  {cart.map((entry) => (
                    <Table.Tr key={entry.product_id}>
                      <Table.Td>{entry.name}</Table.Td>
                      <Table.Td>{entry.qty}</Table.Td>
                      <Table.Td>{entry.price.toFixed(2)}</Table.Td>
                      <Table.Td>{(entry.price * entry.qty).toFixed(2)}</Table.Td>
                      <Table.Td>
                        <ActionIcon
                          color="red"
                          variant="light"
                          size="sm"
                          onClick={() => handleRemoveFromCart(entry.product_id)}
                        >
                          ×
                        </ActionIcon>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>

              {cart.length > 0 && (
                <Box mt="sm">
                  <Divider mb="xs" />
                  <Group justify="flex-end" gap="xs">
                    <Text size="sm" c="dimmed">
                      Subtotal:
                    </Text>
                    <Text size="sm" fw={500}>
                      {subtotal.toFixed(2)}
                    </Text>
                  </Group>
                  {discount > 0 && (
                    <Group justify="flex-end" gap="xs">
                      <Text size="sm" c="dimmed">
                        Discount ({discount}%):
                      </Text>
                      <Text size="sm" c="red">
                        -{discountAmount.toFixed(2)}
                      </Text>
                    </Group>
                  )}
                  <Group justify="flex-end" gap="xs" mt="xs">
                    <Text fw={700} size="lg">
                      TOTAL:
                    </Text>
                    <Text fw={700} size="lg">
                      {total.toFixed(2)}
                    </Text>
                  </Group>
                </Box>
              )}
            </Paper>
          </Stack>
        </Grid.Col>

        {/* ── Right column: Customer + Options + Checkout ── */}
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Stack gap="md">
            {/* Customer */}
            <Paper withBorder p="md" radius="sm">
              <Title order={5} mb="sm">
                Customer
              </Title>
              <Select
                label="Select customer"
                placeholder="No customer (walk-in)"
                data={customerOptions}
                value={selectedCustomerId}
                onChange={handleCustomerChange}
                clearable
                searchable
                mb="sm"
              />

              <Divider label="New customer" labelPosition="left" mb="xs" />
              <Stack gap="xs">
                <TextInput
                  placeholder="Customer name"
                  value={newCustomerName}
                  onChange={(e) => setNewCustomerName(e.currentTarget.value)}
                />
                <NumberInput
                  placeholder="Discount %"
                  min={0}
                  max={100}
                  value={newCustomerDiscount}
                  onChange={setNewCustomerDiscount}
                />
                <Button
                  variant="light"
                  size="xs"
                  loading={createCustomerMutation.isPending}
                  disabled={!newCustomerName.trim()}
                  onClick={() => createCustomerMutation.mutate()}
                >
                  Add customer
                </Button>
              </Stack>
            </Paper>

            {/* Discount & Pay later */}
            <Paper withBorder p="md" radius="sm">
              <Title order={5} mb="sm">
                Sale options
              </Title>
              <Stack gap="sm">
                <NumberInput
                  label="Discount %"
                  min={0}
                  max={100}
                  value={discountPct}
                  onChange={setDiscountPct}
                />
                <Checkbox
                  label="Pay later (debt)"
                  checked={payLater}
                  disabled={!selectedCustomerId}
                  onChange={(e) => setPayLater(e.currentTarget.checked)}
                />
                {!selectedCustomerId && (
                  <Text size="xs" c="dimmed">
                    Select a customer to enable pay later.
                  </Text>
                )}
              </Stack>
            </Paper>

            {/* Checkout */}
            <Button
              size="lg"
              fullWidth
              disabled={cart.length === 0}
              loading={checkoutMutation.isPending}
              onClick={() => checkoutMutation.mutate()}
            >
              Checkout
            </Button>
          </Stack>
        </Grid.Col>
      </Grid>

      {/* ── Receipt Modal ── */}
      <Modal
        opened={receipt !== null}
        onClose={() => setReceipt(null)}
        title={`Receipt #${receipt?.sale_id}`}
        size="md"
      >
        {receipt && (
          <Stack gap="sm">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Date
              </Text>
              <Text size="sm">{new Date(receipt.created_at).toLocaleString()}</Text>
            </Group>
            {receipt.customer_name && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  Customer
                </Text>
                <Text size="sm">{receipt.customer_name}</Text>
              </Group>
            )}

            <Divider />

            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Product</Table.Th>
                  <Table.Th>Qty</Table.Th>
                  <Table.Th>Unit</Table.Th>
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
              <Text size="sm" c="dimmed">
                Subtotal
              </Text>
              <Text size="sm">{receipt.subtotal.toFixed(2)}</Text>
            </Group>
            {receipt.discount_pct > 0 && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  Discount ({receipt.discount_pct}%)
                </Text>
                <Text size="sm" c="red">
                  -{receipt.discount_amount.toFixed(2)}
                </Text>
              </Group>
            )}
            <Group justify="space-between">
              <Text fw={700}>TOTAL</Text>
              <Text fw={700}>{receipt.total.toFixed(2)}</Text>
            </Group>

            <Group justify="center" mt="xs">
              <Badge
                color={receipt.payment_status === "paid" ? "green" : "orange"}
                size="lg"
              >
                {receipt.payment_status.toUpperCase()}
              </Badge>
            </Group>

            <Button fullWidth mt="sm" onClick={() => setReceipt(null)}>
              Close
            </Button>
          </Stack>
        )}
      </Modal>
    </Box>
  );
}
