-- 创建用户表
create table if not exists users (
  id bigint primary key generated always as identity,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  username text unique not null,
  name text not null,
  gender text not null, -- 'male' or 'female'
  age int not null,
  job text,
  mbti text,
  interests text[], -- 数组类型
  location text,
  
  -- JSONB 存储复杂结构，方便扩展
  calibration_data jsonb default '[]'::jsonb,
  preferences jsonb default '{}'::jsonb,
  
  -- V2 新增字段
  password_hash text -- 存储加密后的密码
);

-- 创建匹配记录表 (V2)
create table if not exists match_records (
  id bigint primary key generated always as identity,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  user_a text not null, -- 发起方 username
  user_b text not null, -- 接受方 username
  chat_log jsonb default '[]'::jsonb, -- 完整对话记录
  match_score int default 0, -- 匹配分数
  report text -- 裁判报告摘要
);

-- 开启 Row Level Security (RLS) 
-- 注意：为了演示方便，我们这里暂时允许所有匿名用户读写
-- 在生产环境中，应该配置更严格的策略
alter table users enable row level security;

-- 先删除旧策略（如果存在），防止重复创建报错
drop policy if exists "Enable read access for all users" on users;
drop policy if exists "Enable insert access for all users" on users;
drop policy if exists "Enable update access for all users" on users;

create policy "Enable read access for all users"
on users for select
using (true);

create policy "Enable insert access for all users"
on users for insert
with check (true);

create policy "Enable update access for all users"
on users for update
using (true);
