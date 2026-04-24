<template>
  <el-container class="layout-container">
    <el-aside width="200px" style="background-color: #304156;">
      <div class="logo">注册管理平台</div>
      <el-menu
        default-active="/"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/">批量上传解析</el-menu-item>
        <el-menu-item index="/records">批件台账查看</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </el-main>
  </el-container>
</template>

<script setup>
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
}
.layout-container {
  height: 100vh;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: white;
  font-size: 20px;
  font-weight: bold;
  background: #2b3643;
}
</style>
