import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "@mantine/form";
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
} from "@mantine/core";
import {
  listProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  ApiError,
  type Product,
} from "../api/client";

interface ProductFormValues {
  name: string;
  price: number | string;
}

export default function ProductsPage() {
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [confirmDeleteProduct, setConfirmDeleteProduct] = useState<Product | null>(null);
  const queryClient = useQueryClient();

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["products", search],
    queryFn: () => listProducts(search || undefined),
  });

  const form = useForm<ProductFormValues>({
    initialValues: { name: "", price: "" },
    validate: {
      name: (v) => (String(v).trim().length === 0 ? "Name is required" : null),
      price: (v) => (v === "" || Number(v) < 0 ? "Price must be >= 0" : null),
    },
  });

  function openCreate() {
    setEditingProduct(null);
    form.reset();
    setModalOpen(true);
  }

  function openEdit(product: Product) {
    setEditingProduct(product);
    form.setValues({ name: product.name, price: product.price });
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditingProduct(null);
    form.reset();
  }

  const createMutation = useMutation({
    mutationFn: (data: { name: string; price: number }) => createProduct(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      notifications.show({ color: "green", title: "Success", message: "Product created." });
      closeModal();
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to create product.";
      notifications.show({ color: "red", title: "Error", message: msg });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name?: string; price?: number } }) =>
      updateProduct(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      notifications.show({ color: "green", title: "Success", message: "Product updated." });
      closeModal();
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to update product.";
      notifications.show({ color: "red", title: "Error", message: msg });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteProduct(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      notifications.show({ color: "green", title: "Success", message: "Product deleted." });
      setConfirmDeleteProduct(null);
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to delete product.";
      notifications.show({ color: "red", title: "Error", message: msg });
      setConfirmDeleteProduct(null);
    },
  });

  function handleSubmit(values: ProductFormValues) {
    const price = Number(values.price);
    if (editingProduct) {
      updateMutation.mutate({ id: editingProduct.id, data: { name: values.name.trim(), price } });
    } else {
      createMutation.mutate({ name: values.name.trim(), price });
    }
  }

  const isMutating = createMutation.isPending || updateMutation.isPending;

  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Title order={3}>Products</Title>
        <Button onClick={openCreate}>Add Product</Button>
      </Group>

      <TextInput
        placeholder="Search products..."
        value={search}
        onChange={(e) => setSearch(e.currentTarget.value)}
        mb="md"
        w={300}
      />

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Price</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {isLoading && (
            <Table.Tr>
              <Table.Td colSpan={3}>Loading...</Table.Td>
            </Table.Tr>
          )}
          {!isLoading && products.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={3}>No products found.</Table.Td>
            </Table.Tr>
          )}
          {products.map((p) => (
            <Table.Tr key={p.id}>
              <Table.Td>{p.name}</Table.Td>
              <Table.Td>{p.price.toFixed(2)}</Table.Td>
              <Table.Td>
                <Group gap="xs">
                  <Button size="xs" variant="light" onClick={() => openEdit(p)}>
                    Edit
                  </Button>
                  <ActionIcon
                    color="red"
                    variant="light"
                    size="sm"
                    onClick={() => setConfirmDeleteProduct(p)}
                  >
                    ×
                  </ActionIcon>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {/* Create / Edit Modal */}
      <Modal
        opened={modalOpen}
        onClose={closeModal}
        title={editingProduct ? "Edit Product" : "Add Product"}
      >
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack>
            <TextInput
              label="Name"
              placeholder="Product name"
              {...form.getInputProps("name")}
            />
            <NumberInput
              label="Price"
              placeholder="0.00"
              min={0}
              decimalScale={2}
              {...form.getInputProps("price")}
            />
            <Group justify="flex-end" mt="sm">
              <Button variant="default" onClick={closeModal}>
                Cancel
              </Button>
              <Button type="submit" loading={isMutating}>
                {editingProduct ? "Save" : "Create"}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Confirm Delete Modal */}
      <Modal
        opened={confirmDeleteProduct !== null}
        onClose={() => setConfirmDeleteProduct(null)}
        title="Confirm Delete"
        size="sm"
      >
        <Text mb="md">
          Are you sure you want to delete product{" "}
          <strong>{confirmDeleteProduct?.name}</strong>? Related recipes will also be removed.
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => setConfirmDeleteProduct(null)}>
            Cancel
          </Button>
          <Button
            color="red"
            loading={deleteMutation.isPending}
            onClick={() =>
              confirmDeleteProduct && deleteMutation.mutate(confirmDeleteProduct.id)
            }
          >
            Delete
          </Button>
        </Group>
      </Modal>
    </Box>
  );
}
