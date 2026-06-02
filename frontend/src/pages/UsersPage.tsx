import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
  Title,
  TextInput,
  Button,
  Group,
  Table,
  Modal,
  Select,
  PasswordInput,
  Stack,
  ActionIcon,
  Badge,
  Tooltip,
  Text,
  Box,
} from "@mantine/core";
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  ApiError,
  type User,
} from "../api/client";
import type { Role } from "../lib/roles";

const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "manager", label: "Manager" },
  { value: "salesman", label: "Salesman" },
  { value: "stockman", label: "Stockman" },
];

const ALL_ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "admin", label: "Admin" },
  ...ROLE_OPTIONS,
];

interface UserFormValues {
  username: string;
  password: string;
  role: Role | "";
}

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [confirmDeleteUser, setConfirmDeleteUser] = useState<User | null>(null);
  const queryClient = useQueryClient();

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["users", search],
    queryFn: () => listUsers(search || undefined),
  });

  const form = useForm<UserFormValues>({
    initialValues: { username: "", password: "", role: "" },
    validate: {
      username: (v) => (v.trim().length === 0 ? "Username is required" : null),
      password: (v) => {
        // Password required on create; optional on edit
        if (!editingUser && v.length === 0) return "Password is required";
        return null;
      },
      role: (v) => (v === "" ? "Role is required" : null),
    },
  });

  function openCreate() {
    setEditingUser(null);
    form.reset();
    setModalOpen(true);
  }

  function openEdit(user: User) {
    setEditingUser(user);
    form.setValues({ username: user.username, password: "", role: user.role });
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditingUser(null);
    form.reset();
  }

  const createMutation = useMutation({
    mutationFn: (data: { username: string; password: string; role: Role }) =>
      createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      notifications.show({ color: "green", title: "Success", message: "User created." });
      closeModal();
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to create user.";
      notifications.show({ color: "red", title: "Error", message: msg });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<{ username: string; password: string; role: Role }> }) =>
      updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      notifications.show({ color: "green", title: "Success", message: "User updated." });
      closeModal();
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to update user.";
      notifications.show({ color: "red", title: "Error", message: msg });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      notifications.show({ color: "green", title: "Success", message: "User deleted." });
      setConfirmDeleteUser(null);
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to delete user.";
      notifications.show({ color: "red", title: "Error", message: msg });
      setConfirmDeleteUser(null);
    },
  });

  function handleSubmit(values: UserFormValues) {
    const role = values.role as Role;
    if (editingUser) {
      const data: Partial<{ username: string; password: string; role: Role }> = {
        username: values.username,
        role,
      };
      if (values.password) data.password = values.password;
      updateMutation.mutate({ id: editingUser.id, data });
    } else {
      createMutation.mutate({ username: values.username, password: values.password, role });
    }
  }

  const roleColor: Record<Role, string> = {
    admin: "red",
    manager: "blue",
    salesman: "green",
    stockman: "orange",
  };

  const isMutating = createMutation.isPending || updateMutation.isPending;

  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Title order={3}>Users</Title>
        <Button onClick={openCreate}>Add User</Button>
      </Group>

      <TextInput
        placeholder="Search users..."
        value={search}
        onChange={(e) => setSearch(e.currentTarget.value)}
        mb="md"
        w={300}
      />

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Username</Table.Th>
            <Table.Th>Role</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {isLoading && (
            <Table.Tr>
              <Table.Td colSpan={3}>Loading...</Table.Td>
            </Table.Tr>
          )}
          {!isLoading && users.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={3}>No users found.</Table.Td>
            </Table.Tr>
          )}
          {users.map((u) => (
            <Table.Tr key={u.id}>
              <Table.Td>{u.username}</Table.Td>
              <Table.Td>
                <Badge color={roleColor[u.role]}>{u.role}</Badge>
              </Table.Td>
              <Table.Td>
                <Group gap="xs">
                  <Button size="xs" variant="light" onClick={() => openEdit(u)}>
                    Edit
                  </Button>
                  <Tooltip
                    label={u.username === "admin" ? "Cannot delete the admin user" : "Delete user"}
                    disabled={u.username !== "admin"}
                  >
                    <span>
                      <ActionIcon
                        color="red"
                        variant="light"
                        size="sm"
                        disabled={u.username === "admin"}
                        onClick={() => setConfirmDeleteUser(u)}
                      >
                        ×
                      </ActionIcon>
                    </span>
                  </Tooltip>
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
        title={editingUser ? "Edit User" : "Add User"}
      >
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack>
            <TextInput
              label="Username"
              placeholder="Username"
              {...form.getInputProps("username")}
            />
            <PasswordInput
              label={editingUser ? "Password (leave blank to keep current)" : "Password"}
              placeholder="Password"
              {...form.getInputProps("password")}
            />
            <Select
              label="Role"
              placeholder="Select role"
              data={editingUser ? ALL_ROLE_OPTIONS : ROLE_OPTIONS}
              {...form.getInputProps("role")}
            />
            <Group justify="flex-end" mt="sm">
              <Button variant="default" onClick={closeModal}>
                Cancel
              </Button>
              <Button type="submit" loading={isMutating}>
                {editingUser ? "Save" : "Create"}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Confirm Delete Modal */}
      <Modal
        opened={confirmDeleteUser !== null}
        onClose={() => setConfirmDeleteUser(null)}
        title="Confirm Delete"
        size="sm"
      >
        <Text mb="md">
          Are you sure you want to delete user <strong>{confirmDeleteUser?.username}</strong>?
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => setConfirmDeleteUser(null)}>
            Cancel
          </Button>
          <Button
            color="red"
            loading={deleteMutation.isPending}
            onClick={() => confirmDeleteUser && deleteMutation.mutate(confirmDeleteUser.id)}
          >
            Delete
          </Button>
        </Group>
      </Modal>
    </Box>
  );
}
