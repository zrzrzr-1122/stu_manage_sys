<template>
  <v-card rounded="lg" class="pa-6">
    <div class="text-h6 mb-4">个人信息</div>
    <v-row>
      <v-col cols="12" md="6"><v-text-field label="学号" :model-value="form.stu_id" disabled /></v-col>
      <v-col cols="12" md="6"><v-text-field label="姓名" :model-value="form.stu_name" disabled /></v-col>
      <v-col cols="12" md="6"><v-text-field label="班级ID" :model-value="form.class_id" disabled /></v-col>
      <v-col cols="12" md="6"><v-text-field label="学历" :model-value="form.education" disabled /></v-col>
      <v-col cols="12" md="6"><v-text-field v-model="form.major" label="专业" /></v-col>
      <v-col cols="12" md="6"><v-text-field v-model="form.graduateSchool" label="毕业学校" /></v-col>
      <v-col cols="12"><v-text-field v-model="form.address" label="籍贯" /></v-col>
    </v-row>
    <v-btn color="primary" :loading="saving" @click="save">保存可修改项</v-btn>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import http from "@/api/http";

const form = reactive<Record<string, any>>({});
const saving = ref(false);

onMounted(async () => {
  Object.assign(form, await http.get("/me"));
});

async function save() {
  saving.value = true;
  try {
    await http.put("/me", {
      address: form.address,
      graduateSchool: form.graduateSchool,
      major: form.major,
    });
    alert("保存成功");
  } catch (e: any) {
    alert(e.message);
  } finally {
    saving.value = false;
  }
}
</script>
