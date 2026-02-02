<template>
  <div id="app">
    <el-container>
      <el-header class="header">
        <div class="header-content">
          <h1>AI漫剧剧本生成系统</h1>
          <nav class="nav-menu">
            <router-link to="/" class="nav-link">
              <el-icon><Edit /></el-icon>
              剧本生成
            </router-link>
            <router-link to="/story-units" class="nav-link">
              <el-icon><List /></el-icon>
              剧情单元
            </router-link>
          </nav>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
</script>

<style scoped>
#app {
  min-height: 100vh;
  background: #f5f7fa;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.nav-menu {
  display: flex;
  gap: 20px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  color: white;
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 4px;
  transition: all 0.3s;
  font-size: 14px;
}

.nav-link:hover,
.nav-link.router-link-active {
  background: rgba(255, 255, 255, 0.2);
}

.nav-link .el-icon {
  font-size: 16px;
}
</style>
