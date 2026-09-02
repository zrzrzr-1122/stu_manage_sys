<template>
  <v-main class="login-bg d-flex align-center">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" sm="8" md="5" lg="4">
          <v-card rounded="xl" elevation="8" class="pa-6">
            <div class="text-h5 font-weight-bold mb-1">沃林学生门户</div>
            <div class="text-medium-emphasis mb-6">使用学号登录，查看成绩与就业信息</div>
            <v-text-field
              id="portal-login-stu-id"
              v-model="stuId"
              label="学号"
              type="number"
              autocomplete="username"
              prepend-inner-icon="mdi-card-account-details"
            />
            <v-text-field
              id="portal-login-password"
              v-model="password"
              label="密码"
              :type="showPwd ? 'text' : 'password'"
              autocomplete="current-password"
              prepend-inner-icon="mdi-lock"
              :append-inner-icon="showPwd ? 'mdi-eye-off' : 'mdi-eye'"
              @click:append-inner="showPwd = !showPwd"
              @keyup.enter="login"
            />
            <v-btn color="primary" block size="large" :loading="loading" @click="login">登录</v-btn>
            <div class="text-caption text-medium-emphasis mt-4">默认密码：123456（由管理员创建学生时生成）</div>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </v-main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import http from "@/api/http";

const router = useRouter();
const stuId = ref("");
const password = ref("123456");
const showPwd = ref(false);
const loading = ref(false);

async function login() {
  if (!stuId.value || !password.value) return;
  loading.value = true;
  try {
    const data = await http.post("/login", {
      stu_id: Number(stuId.value),
      password: password.value,
    });
    localStorage.setItem("portal_token", data.accessToken);
    localStorage.setItem("portal_name", data.stuName);
    router.push("/home");
  } catch (e: any) {
    alert(e.message || "登录失败");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-bg {
  min-height: 100vh;
  background: linear-gradient(135deg, #165dff 0%, #6aa1ff 50%, #e8f1ff 100%);
}
</style>
