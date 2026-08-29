<template>
  <v-card rounded="lg">
    <v-card-title>我的成绩</v-card-title>
    <v-progress-linear v-if="loading" indeterminate />
    <v-table>
      <thead>
        <tr>
          <th>考核序次</th>
          <th>分数</th>
          <th>姓名</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in list" :key="item.id">
          <td>{{ item.exam_order }}</td>
          <td>{{ item.score }}</td>
          <td>{{ item.stu_name }}</td>
        </tr>
        <tr v-if="!list.length">
          <td colspan="3" class="text-center text-medium-emphasis py-6">暂无成绩</td>
        </tr>
      </tbody>
    </v-table>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import http from "@/api/http";

const loading = ref(false);
const list = ref<any[]>([]);

onMounted(async () => {
  loading.value = true;
  try {
    list.value = (await http.get("/scores")) || [];
  } finally {
    loading.value = false;
  }
});
</script>
