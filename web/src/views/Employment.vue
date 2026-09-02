<template>
  <v-card rounded="lg" class="pa-6">
    <div class="text-h6 mb-4">就业信息</div>
    <template v-if="info">
      <v-list>
        <v-list-item title="公司" :subtitle="info.company || '-'" />
        <v-list-item title="薪资" :subtitle="info.salary != null ? String(info.salary) : '-'" />
        <v-list-item title="就业开放时间" :subtitle="formatDate(info.open_time) || '-'" />
        <v-list-item title="Offer 时间" :subtitle="formatDate(info.offer_time) || '-'" />
        <v-list-item title="班级ID" :subtitle="String(info.class_id ?? '-')" />
      </v-list>
    </template>
    <v-alert v-else type="info" variant="tonal">暂无就业记录</v-alert>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import http from "@/api/http";
import { formatDate } from "@/utils/date";

const info = ref<Record<string, any> | null>(null);

onMounted(async () => {
  info.value = (await http.get("/employment")) || null;
});
</script>
