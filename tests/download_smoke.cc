#include <rime_api.h>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

int main(int argc, char** argv) {
  if (argc != 3) return 2;
  auto* api = rime_get_api();
  RIME_STRUCT(RimeTraits, traits);
  const char* modules[] = {"default", "lua", nullptr};
  traits.user_data_dir = argv[1];
  traits.shared_data_dir = argv[2];
  traits.app_name = "rime.download-check";
  traits.modules = modules;
  traits.min_log_level = 2;
  api->setup(&traits);
  api->initialize(&traits);
  auto session = api->create_session();
  int result = 0;
  try {
    auto select = [&](const char* schema) {
      api->clear_composition(session);
      if (!api->select_schema(session, schema))
        throw std::runtime_error(std::string("Cannot load schema: ") + schema);
      for (const auto* option : {"ascii_mode", "pinyin", "emoji_cn", "simplification",
                                 "charset_comment_filter", "udpf_switch"})
        api->set_option(session, option, false);
      api->set_option(session, "extended_char", true);
    };
    auto check = [&](const char* keys, const char* expected, const char* comment = "") {
      api->clear_composition(session);
      api->simulate_key_sequence(session, keys);
      std::vector<std::pair<std::string, std::string>> candidates;
      RIME_STRUCT(RimeContext, context);
      if (api->get_context(session, &context)) {
        for (int i = 0; i < context.menu.num_candidates; ++i) {
          const auto& c = context.menu.candidates[i];
          candidates.emplace_back(c.text ? c.text : "", c.comment ? c.comment : "");
        }
        api->free_context(&context);
      }
      std::string committed;
      RIME_STRUCT(RimeCommit, commit);
      if (api->get_commit(session, &commit)) {
        committed = commit.text ? commit.text : "";
        api->free_commit(&commit);
      }
      bool found = !*expected ? candidates.empty() && committed.empty()
                             : !*comment && committed == expected;
      for (const auto& c : candidates)
        found |= *expected && c.first == expected && c.second.find(comment) != std::string::npos;
      if (!found)
        throw std::runtime_error(std::string("Unexpected candidates for ") + keys + ": expected " + expected);
    };

    select("flypy");
    check("ni", "你");
    check("nirx", "你");
    check(";w", "？");
    check("aary", "");
    check("aary{Control+h}", "𠼞");
    check("aary", "𠼞");
    api->set_option(session, "charset_comment_filter", true);
    api->set_option(session, "udpf_switch", true);
    check("~aary", "𠼞", "[扩B] U+20F1E");
    api->set_option(session, "extended_char", true);
    check("~aary", "");
    check("`ni", "你", "nirx");
    select("tiger");
    check("n", "在");
    select("tigress");
    check("n", "现在");
    select("lansanguanfang");
    check("n", "你");
    // 空格提交首选，覆盖新词频排序，也覆盖“未按主观喜好改频”的同码组。
    check("tjaf{space}", "魔法");
    check("dmjv{space}", "屋子");
    check("obwc{space}", "格式");
    check("hjsm{space}", "就不是");
    check("eohn{space}", "询问");
    check("nrnd{space}", "唱着");
    // 恢复旧官方字词位置，同时保护原本词在字前的编码。
    check("tonm{space}", "狗");
    check("komb{space}", "侵");
    check("hofq{space}", "朵");
    check("hepi{space}", "豆蔻");
    check("aipg;", "淙");  // 演示、淙、泳帽：保留字夹在两段词之间的位置。
    // 旧表仅有单字的编码，新增词不能挤到该字之前。
    check("eiiu{space}", "慈");
    check("yjjw{space}", "个");
    select("jaroomaji");
    check("nihon", "日本");
    std::cout << "PASS: five schemas, Lansan phrase order, Flypy charset switching, reverse lookup and Unicode comments\n";
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    result = 1;
  }
  api->destroy_session(session);
  api->finalize();
  return result;
}
