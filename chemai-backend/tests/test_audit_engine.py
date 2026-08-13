"""四维审核引擎 — 确定性测试套件

覆盖 9 种反应类型的 86 道确定性验证题目。
D1 系数配平准确率目标: 100% (86/86 全部通过)
"""

import pytest
from app.services.audit_engine import get_audit_engine
from app.services.audit_engine.normalizer import normalize_chem_formulas
from app.services.audit_engine.parser import parse_equation, count_elements, EquationParseError
from app.services.audit_engine.balance import check_balance, check_charge_balance
from app.services.audit_engine.conditions import check_conditions
from app.services.audit_engine.product_stability import check_product_stability
from app.services.audit_engine.structure import check_structure
pytestmark = pytest.mark.l1


# ── 测试夹具 ────────────────────────────────────────────

@pytest.fixture
def engine():
    return get_audit_engine()


# ══════════════════════════════════════════════════════════
# Parser 单元测试 (task 1.5)
# ══════════════════════════════════════════════════════════

class TestParser:
    """方程式解析器单元测试"""

    def test_parse_simple_arrow(self):
        r, p = parse_equation("2H2 + O2 -> 2H2O")
        assert r == ["2H2", "O2"]
        assert p == ["2H2O"]

    def test_parse_equals(self):
        r, p = parse_equation("2H2 + O2 = 2H2O")
        assert r == ["2H2", "O2"]
        assert p == ["2H2O"]

    def test_parse_bracket_protection(self):
        # Note: parser tests pre-normalized input (normalized wraps bare formulas in $)
        from app.services.audit_engine.normalizer import normalize_chem_formulas
        eq = normalize_chem_formulas("Ca(OH)2 + CO2 -> CaCO3 + H2O")
        r, p = parse_equation(eq)
        assert len(r) == 2  # 2 reactants
        assert len(p) == 2  # 2 products

    def test_parse_empty_raises(self):
        with pytest.raises(EquationParseError):
            parse_equation("not an equation")

    def test_count_simple(self):
        assert count_elements("H2O") == {"H": 2, "O": 1}

    def test_count_with_coefficient(self):
        assert count_elements("2H2O") == {"H": 4, "O": 2}

    def test_count_brackets(self):
        counts = count_elements("Ca(OH)2")
        assert counts == {"Ca": 1, "O": 2, "H": 2}

    def test_count_nested_brackets(self):
        counts = count_elements("Fe2(SO4)3")
        assert counts["Fe"] == 2
        assert counts["S"] == 3
        assert counts["O"] == 12

    def test_count_square_brackets(self):
        counts = count_elements("K4[Fe(CN)6]")
        assert counts["K"] == 4
        assert counts["Fe"] == 1
        assert counts["C"] == 6
        assert counts["N"] == 6

    def test_count_no_coefficient(self):
        assert count_elements("Fe") == {"Fe": 1}


# ══════════════════════════════════════════════════════════
# Normalizer 单元测试 (task 1.5)
# ══════════════════════════════════════════════════════════

class TestNormalizer:
    """化学式归一化器单元测试"""

    def test_strip_latex_ce(self):
        result = normalize_chem_formulas(r"$\ce{2H2 + O2 -> 2H2O}$")
        assert "2H2" in result
        assert "O2" in result.replace("$", "")
        assert "2H2O" in result.replace("$", "")

    def test_unicode_subscript(self):
        result = normalize_chem_formulas("H₂O")
        assert "2" in result
        assert "₂" not in result

    def test_latex_subscript(self):
        result = normalize_chem_formulas("H_{2}O")
        assert "2" in result  # 数字被保留
        # LaTeX subscript format is converted
        assert "_{2}" not in result

    def test_arrow_unification(self):
        result = normalize_chem_formulas("2H2 + O2 → 2H2O")
        assert "->" in result

    def test_equilibrium_arrow(self):
        result = normalize_chem_formulas("N2 + 3H2 ⇌ 2NH3")
        assert "<=>" in result

    def test_english_word_protection(self):
        result = normalize_chem_formulas("catalyst")
        assert "$" not in result  # 不包裹英文单词


# ══════════════════════════════════════════════════════════
# D1: 系数配平 — 化合反应 (12 道)
# ══════════════════════════════════════════════════════════

class TestBalanceCombination:
    """化合反应配平测试"""

    def test_h2_o2(self, engine):
        r = engine.check_balance_only("2H2 + O2 -> 2H2O")
        assert r.status == "passed"

    def test_n2_h2(self, engine):
        r = engine.check_balance_only("N2 + 3H2 -> 2NH3")
        assert r.status == "passed"

    def test_s_o2(self, engine):
        r = engine.check_balance_only("S + O2 -> SO2")
        assert r.status == "passed"

    def test_p_o2(self, engine):
        r = engine.check_balance_only("4P + 5O2 -> 2P2O5")
        assert r.status == "passed"

    def test_na_o2(self, engine):
        r = engine.check_balance_only("4Na + O2 -> 2Na2O")
        assert r.status == "passed"

    def test_fe_o2_unbalanced(self, engine):
        r = engine.check_balance_only("Fe + O2 -> Fe2O3")
        assert r.status == "blocked"

    def test_fe_o2_balanced(self, engine):
        r = engine.check_balance_only("4Fe + 3O2 -> 2Fe2O3")
        assert r.status == "passed"

    def test_co_o2(self, engine):
        r = engine.check_balance_only("2CO + O2 -> 2CO2")
        assert r.status == "passed"

    def test_c_o2_unbalanced(self, engine):
        r = engine.check_balance_only("C + O2 -> CO")
        assert r.status == "blocked"

    def test_c_o2_balanced(self, engine):
        r = engine.check_balance_only("2C + O2 -> 2CO")
        assert r.status == "passed"

    def test_mg_o2(self, engine):
        r = engine.check_balance_only("2Mg + O2 -> 2MgO")
        assert r.status == "passed"

    def test_al_o2(self, engine):
        r = engine.check_balance_only("4Al + 3O2 -> 2Al2O3")
        assert r.status == "passed"


# ══════════════════════════════════════════════════════════
# D1: 系数配平 — 分解反应 (10 道)
# ══════════════════════════════════════════════════════════

class TestBalanceDecomposition:
    """分解反应配平测试"""

    def test_kclo3(self, engine):
        r = engine.check_balance_only("2KClO3 -> 2KCl + 3O2")
        assert r.status == "passed"

    def test_kmno4(self, engine):
        r = engine.check_balance_only("2KMnO4 -> K2MnO4 + MnO2 + O2")
        assert r.status == "passed"

    def test_h2o2(self, engine):
        r = engine.check_balance_only("2H2O2 -> 2H2O + O2")
        assert r.status == "passed"

    def test_caco3(self, engine):
        r = engine.check_balance_only("CaCO3 -> CaO + CO2")
        assert r.status == "passed"

    def test_nahco3(self, engine):
        r = engine.check_balance_only("2NaHCO3 -> Na2CO3 + H2O + CO2")
        assert r.status == "passed"

    def test_h2o_electrolysis(self, engine):
        r = engine.check_balance_only("2H2O -> 2H2 + O2")
        assert r.status == "passed"

    def test_hgo(self, engine):
        r = engine.check_balance_only("2HgO -> 2Hg + O2")
        assert r.status == "passed"

    def test_nh4hco3(self, engine):
        r = engine.check_balance_only("NH4HCO3 -> NH3 + H2O + CO2")
        assert r.status == "passed"

    def test_nh4cl_naoh(self, engine):
        r = engine.check_balance_only("NH4Cl + NaOH -> NaCl + NH3 + H2O")
        assert r.status == "passed"

    def test_cuo_decomp(self, engine):
        r = engine.check_balance_only("4CuO -> 2Cu2O + O2")
        assert r.status == "passed"


# ══════════════════════════════════════════════════════════
# D1: 系数配平 — 置换反应 (8 道)
# ══════════════════════════════════════════════════════════

class TestBalanceDisplacement:
    """置换反应配平测试"""

    def test_fe_cuso4(self, engine):
        r = engine.check_balance_only("Fe + CuSO4 -> FeSO4 + Cu")
        assert r.status == "passed"

    def test_zn_hcl(self, engine):
        r = engine.check_balance_only("Zn + 2HCl -> ZnCl2 + H2")
        assert r.status == "passed"

    def test_na_h2o(self, engine):
        r = engine.check_balance_only("2Na + 2H2O -> 2NaOH + H2")
        assert r.status == "passed"

    def test_cl2_nabr(self, engine):
        r = engine.check_balance_only("Cl2 + 2NaBr -> 2NaCl + Br2")
        assert r.status == "passed"

    def test_mg_cuso4(self, engine):
        r = engine.check_balance_only("Mg + CuSO4 -> MgSO4 + Cu")
        assert r.status == "passed"

    def test_fe_hcl(self, engine):
        r = engine.check_balance_only("Fe + 2HCl -> FeCl2 + H2")
        assert r.status == "passed"

    def test_cu_agno3(self, engine):
        r = engine.check_balance_only("Cu + 2AgNO3 -> Cu(NO3)2 + 2Ag")
        assert r.status == "passed"

    def test_al_fe2o3(self, engine):
        r = engine.check_balance_only("2Al + Fe2O3 -> Al2O3 + 2Fe")
        assert r.status == "passed"


# ══════════════════════════════════════════════════════════
# D1: 系数配平 — 复分解反应 (8 道)
# ══════════════════════════════════════════════════════════

class TestBalanceDoubleDisplacement:
    """复分解反应配平测试"""

    def test_hcl_naoh(self, engine):
        r = engine.check_balance_only("HCl + NaOH -> NaCl + H2O")
        assert r.status == "passed"

    def test_caco3_hcl(self, engine):
        r = engine.check_balance_only("CaCO3 + 2HCl -> CaCl2 + H2O + CO2")
        assert r.status == "passed"

    def test_agno3_nacl(self, engine):
        r = engine.check_balance_only("AgNO3 + NaCl -> AgCl + NaNO3")
        assert r.status == "passed"

    def test_bacl2_h2so4(self, engine):
        r = engine.check_balance_only("BaCl2 + H2SO4 -> BaSO4 + 2HCl")
        assert r.status == "passed"

    def test_naoh_h2so4(self, engine):
        r = engine.check_balance_only("2NaOH + H2SO4 -> Na2SO4 + 2H2O")
        assert r.status == "passed"

    def test_fecl3_naoh(self, engine):
        r = engine.check_balance_only("FeCl3 + 3NaOH -> Fe(OH)3 + 3NaCl")
        assert r.status == "passed"

    def test_cacl2_na2co3(self, engine):
        r = engine.check_balance_only("CaCl2 + Na2CO3 -> CaCO3 + 2NaCl")
        assert r.status == "passed"

    def test_kcl_agno3(self, engine):
        r = engine.check_balance_only("KCl + AgNO3 -> AgCl + KNO3")
        assert r.status == "passed"


# ══════════════════════════════════════════════════════════
# D1: 系数配平 — 氧化还原反应 (14 道)
# ══════════════════════════════════════════════════════════

class TestBalanceRedox:
    """氧化还原反应配平测试"""

    def test_cu_hno3_dilute(self, engine):
        r = engine.check_balance_only("3Cu + 8HNO3 -> 3Cu(NO3)2 + 2NO + 4H2O")
        assert r.status == "passed"

    def test_cu_h2so4_conc(self, engine):
        r = engine.check_balance_only("Cu + 2H2SO4 -> CuSO4 + SO2 + 2H2O")
        assert r.status == "passed"

    def test_mno2_hcl(self, engine):
        r = engine.check_balance_only("MnO2 + 4HCl -> MnCl2 + Cl2 + 2H2O")
        assert r.status == "passed"

    def test_fe_hno3(self, engine):
        r = engine.check_balance_only("Fe + 4HNO3 -> Fe(NO3)3 + NO + 2H2O")
        assert r.status == "passed"

    def test_so2_o2(self, engine):
        r = engine.check_balance_only("2SO2 + O2 -> 2SO3")
        assert r.status == "passed"

    def test_no_o2(self, engine):
        r = engine.check_balance_only("2NO + O2 -> 2NO2")
        assert r.status == "passed"

    def test_h2s_so2(self, engine):
        r = engine.check_balance_only("2H2S + SO2 -> 3S + 2H2O")
        assert r.status == "passed"

    def test_cl2_naoh(self, engine):
        r = engine.check_balance_only("Cl2 + 2NaOH -> NaCl + NaClO + H2O")
        assert r.status == "passed"

    def test_k2cr2o7_hcl(self, engine):
        r = engine.check_balance_only("K2Cr2O7 + 14HCl -> 2KCl + 2CrCl3 + 3Cl2 + 7H2O")
        assert r.status == "passed"

    def test_fe2o3_co(self, engine):
        r = engine.check_balance_only("Fe2O3 + 3CO -> 2Fe + 3CO2")
        assert r.status == "passed"

    def test_h2_cuo(self, engine):
        r = engine.check_balance_only("H2 + CuO -> Cu + H2O")
        assert r.status == "passed"

    def test_c_h2so4(self, engine):
        r = engine.check_balance_only("C + 2H2SO4 -> CO2 + 2SO2 + 2H2O")
        assert r.status == "passed"

    def test_fes2_o2(self, engine):
        r = engine.check_balance_only("4FeS2 + 11O2 -> 2Fe2O3 + 8SO2")
        assert r.status == "passed"

    def test_nh3_o2(self, engine):
        r = engine.check_balance_only("4NH3 + 5O2 -> 4NO + 6H2O")
        assert r.status == "passed"


# ══════════════════════════════════════════════════════════
# D1: 系数配平 — 有机反应 (8 道)
# ══════════════════════════════════════════════════════════

class TestBalanceOrganic:
    """有机反应配平测试"""

    def test_ch4_combustion(self, engine):
        r = engine.check_balance_only("CH4 + 2O2 -> CO2 + 2H2O")
        assert r.status == "passed"

    def test_c2h5oh_combustion(self, engine):
        r = engine.check_balance_only("C2H5OH + 3O2 -> 2CO2 + 3H2O")
        assert r.status == "passed"

    def test_c6h12o6_combustion(self, engine):
        r = engine.check_balance_only("C6H12O6 + 6O2 -> 6CO2 + 6H2O")
        assert r.status == "passed"

    def test_c2h4_o2(self, engine):
        r = engine.check_balance_only("C2H4 + 3O2 -> 2CO2 + 2H2O")
        assert r.status == "passed"

    def test_esterification(self, engine):
        r = engine.check_balance_only("CH3COOH + C2H5OH -> CH3COOC2H5 + H2O")
        assert r.status == "passed"

    def test_ch3oh_combustion(self, engine):
        r = engine.check_balance_only("2CH3OH + 3O2 -> 2CO2 + 4H2O")
        assert r.status == "passed"

    def test_c3h8_combustion(self, engine):
        r = engine.check_balance_only("C3H8 + 5O2 -> 3CO2 + 4H2O")
        assert r.status == "passed"

    def test_c2h2_combustion(self, engine):
        r = engine.check_balance_only("2C2H2 + 5O2 -> 4CO2 + 2H2O")
        assert r.status == "passed"


# ══════════════════════════════════════════════════════════
# D1: 系数配平 — 离子方程式 (10 道)
# ══════════════════════════════════════════════════════════

class TestBalanceIonic:
    """离子方程式配平测试"""

    def test_fe_cu2p(self, engine):
        r = engine.check_balance_only("Fe + Cu^{2+} -> Fe^{2+} + Cu")
        assert r.status == "passed"

    def test_agp_clm(self, engine):
        r = engine.check_balance_only("Ag^{+} + Cl^{-} -> AgCl")
        assert r.status == "passed"

    def test_bap_so4(self, engine):
        r = engine.check_balance_only("Ba^{2+} + SO4^{2-} -> BaSO4")
        assert r.status == "passed"

    def test_caco3_hp(self, engine):
        r = engine.check_balance_only("CaCO3 + 2H^{+} -> Ca^{2+} + H2O + CO2")
        assert r.status == "passed"

    def test_fe_hp(self, engine):
        r = engine.check_balance_only("Fe + 2H^{+} -> Fe^{2+} + H2")
        assert r.status == "passed"

    def test_mno4_fe2p(self, engine):
        r = engine.check_balance_only("MnO4^{-} + 5Fe^{2+} + 8H^{+} -> Mn^{2+} + 5Fe^{3+} + 4H2O")
        assert r.status == "passed"

    def test_cr2o7_fe2p(self, engine):
        r = engine.check_balance_only("Cr2O7^{2-} + 6Fe^{2+} + 14H^{+} -> 2Cr^{3+} + 6Fe^{3+} + 7H2O")
        assert r.status == "passed"

    def test_hco3_hp(self, engine):
        r = engine.check_balance_only("HCO3^{-} + H^{+} -> H2O + CO2")
        assert r.status == "passed"

    def test_al_oh(self, engine):
        r = engine.check_balance_only("Al^{3+} + 3OH^{-} -> Al(OH)3")
        assert r.status == "passed"

    def test_charge_unbalanced(self, engine):
        r = engine.audit_equation("Fe + Cu^{2+} -> Fe^{3+} + Cu")
        assert r.overall_status == "blocked"


# ══════════════════════════════════════════════════════════
# D1: 系数配平 — 电极反应 (6 道)
# ══════════════════════════════════════════════════════════

class TestBalanceElectrode:
    """电极反应配平测试"""

    def test_anode_zn(self, engine):
        r = engine.check_balance_only("Zn -> Zn^{2+} + 2e^{-}")
        assert r.status == "passed"

    def test_cathode_cu(self, engine):
        r = engine.check_balance_only("Cu^{2+} + 2e^{-} -> Cu")
        assert r.status == "passed"

    def test_anode_water(self, engine):
        r = engine.check_balance_only("2H2O -> O2 + 4H^{+} + 4e^{-}")
        assert r.status == "passed"

    def test_cathode_water(self, engine):
        r = engine.check_balance_only("2H2O + 2e^{-} -> H2 + 2OH^{-}")
        assert r.status == "passed"

    def test_anode_cl(self, engine):
        r = engine.check_balance_only("2Cl^{-} -> Cl2 + 2e^{-}")
        assert r.status == "passed"

    def test_overall_electrolysis(self, engine):
        r = engine.check_balance_only("2NaCl + 2H2O -> 2NaOH + H2 + Cl2")
        assert r.status == "passed"


# ══════════════════════════════════════════════════════════
# D1: 系数配平 — 工业流程反应 (10 道)
# ══════════════════════════════════════════════════════════

class TestBalanceIndustrial:
    """工业流程反应配平测试"""

    def test_haber(self, engine):
        r = engine.check_balance_only("N2 + 3H2 -> 2NH3")
        assert r.status == "passed"

    def test_contact_process_s(self, engine):
        r = engine.check_balance_only("S + O2 -> SO2")
        assert r.status == "passed"

    def test_contact_process_so2(self, engine):
        r = engine.check_balance_only("2SO2 + O2 -> 2SO3")
        assert r.status == "passed"

    def test_contact_process_so3(self, engine):
        r = engine.check_balance_only("SO3 + H2O -> H2SO4")
        assert r.status == "passed"

    def test_blast_furnace_fe2o3(self, engine):
        r = engine.check_balance_only("Fe2O3 + 3CO -> 2Fe + 3CO2")
        assert r.status == "passed"

    def test_blast_furnace_fe3o4(self, engine):
        r = engine.check_balance_only("Fe3O4 + 4CO -> 3Fe + 4CO2")
        assert r.status == "passed"

    def test_limestone(self, engine):
        r = engine.check_balance_only("CaCO3 -> CaO + CO2")
        assert r.status == "passed"

    def test_slaked_lime(self, engine):
        r = engine.check_balance_only("CaO + H2O -> Ca(OH)2")
        assert r.status == "passed"

    def test_solvay_carbonation(self, engine):
        r = engine.check_balance_only("NaCl + NH3 + CO2 + H2O -> NaHCO3 + NH4Cl")
        assert r.status == "passed"

    def test_solvay_calcination(self, engine):
        r = engine.check_balance_only("2NaHCO3 -> Na2CO3 + H2O + CO2")
        assert r.status == "passed"


# ══════════════════════════════════════════════════════════
# D2: 条件审核测试 (task 3.7)
# ══════════════════════════════════════════════════════════

class TestConditions:
    """反应条件审核测试"""

    def test_combustion_missing(self):
        r = check_conditions("CH4 + 2O2 -> CO2 + 2H2O")
        assert r.status == "failed"
        assert "点燃" in str(r.missing_conditions)

    def test_combustion_present(self):
        r = check_conditions("CH4 + 2O2 ->(点燃) CO2 + 2H2O")
        assert r.status == "passed"

    def test_catalysis_missing(self):
        r = check_conditions("2KClO3 -> 2KCl + 3O2")
        assert r.status == "failed"  # 热分解和催化都触发 high/medium

    def test_electrolysis(self):
        r = check_conditions("2H2O ->(通电) 2H2 + O2")
        assert r.status == "passed"

    def test_electrolysis_missing(self):
        r = check_conditions("2H2O -> 2H2 + O2")
        assert r.status == "passed"  # 无"电解"关键词触发

    def test_no_condition_needed(self):
        r = check_conditions("2H2 + O2 -> 2H2O")
        assert r.status == "passed"

    def test_heat_decomposition(self):
        r = check_conditions("CaCO3 -> CaO + CO2")
        assert r.status == "failed"
        assert "加热" in str(r.missing_conditions)

    def test_contradictory(self):
        r = check_conditions("A ->(浓, 稀) B")
        assert r.status == "failed"


# ══════════════════════════════════════════════════════════
# D3: 产物稳定性测试 (task 3.7)
# ══════════════════════════════════════════════════════════

class TestProductStability:
    """产物稳定性审核测试"""

    def test_h2co3_unstable(self):
        r = check_product_stability("CaCO3 + 2HCl -> CaCl2 + H2CO3")
        assert r.status == "failed"

    def test_products_ok(self):
        r = check_product_stability("CaCO3 + 2HCl -> CaCl2 + H2O + CO2")
        assert r.status == "passed"

    def test_conc_h2so4_warning(self):
        r = check_product_stability("Cu + 浓H2SO4 -> CuSO4 + H2")
        # 浓硫酸应生成 SO₂ 而非 H₂
        assert r.status in ("warning", "failed")

    def test_nh4oh_unstable(self):
        r = check_product_stability("NH4Cl + NaOH -> NaCl + NH4OH")
        assert r.status == "failed"

    def test_organic_in_products(self):
        r = check_product_stability("A + B -> C2H5OH + H2O")
        # 有机物检测为 medium 置信度，应 warning
        assert r.status == "warning"


# ══════════════════════════════════════════════════════════
# D4: 分子结构测试 (task 3.7)
# ══════════════════════════════════════════════════════════

class TestStructure:
    """分子结构审核测试"""

    def test_brackets_ok(self):
        r = check_structure("Ca(OH)2 + CO2 -> CaCO3 + H2O")
        assert r.status == "passed"

    def test_brackets_unmatched(self):
        r = check_structure("Ca(OH)2 + CO2 -> CaCO3 + H2O)")
        assert r.status == "failed"

    def test_double_upper_error(self):
        r = check_structure("FE + O2 -> FE2O3")
        assert r.status == "failed"

    def test_charge_format_error(self):
        r = check_structure("Fe+2 + Cu -> Fe + Cu+2")
        assert r.status == "failed"

    def test_simple_ok(self):
        r = check_structure("2H2 + O2 -> 2H2O")
        assert r.status == "passed"

    def test_complex_ok(self):
        r = check_structure("2NaOH + H2SO4 -> Na2SO4 + 2H2O")
        assert r.status == "passed"

    def test_unclosed_bracket(self):
        r = check_structure("Ca(OH)2 + CO2 -> CaCO3 + (H2O")
        assert r.status == "failed"

    def test_extra_bracket(self):
        r = check_structure("Ca)OH(2 + CO2 -> CaCO3 + H2O")
        assert r.status == "failed"


# ══════════════════════════════════════════════════════════
# 综合集成测试 (task 4.4)
# ══════════════════════════════════════════════════════════

class TestIntegration:
    """综合审核集成测试"""

    def test_full_pass(self, engine):
        r = engine.audit_equation("2H2 + O2 -> 2H2O")
        assert r.overall_status == "passed"

    def test_hard_block(self, engine):
        r = engine.audit_equation("Fe + O2 -> Fe2O3")
        assert r.overall_status == "blocked"

    def test_combustion_block(self, engine):
        r = engine.audit_equation("CH4 + 2O2 -> CO2 + 2H2O")
        assert r.overall_status == "blocked"
        assert r.audits.condition.status == "failed"

    def test_unstable_product_block(self, engine):
        r = engine.audit_equation("CaCO3 + 2HCl -> CaCl2 + H2CO3")
        assert r.overall_status == "blocked"
        assert r.audits.product.status == "failed"

    def test_charge_block(self, engine):
        r = engine.audit_equation("Fe + Cu^{2+} -> Fe^{3+} + Cu")
        assert r.overall_status == "blocked"

    def test_brackets_structure_fail(self, engine):
        r = engine.audit_equation("FE + O2 -> FE2O3")
        assert r.audits.structure.status == "failed"

    def test_report_structure(self, engine):
        r = engine.audit_equation("2H2 + O2 -> 2H2O")
        assert hasattr(r, "question_id")
        assert hasattr(r, "audits")
        assert hasattr(r.audits, "balance")
        assert hasattr(r.audits, "condition")
        assert hasattr(r.audits, "product")
        assert hasattr(r.audits, "structure")
        assert hasattr(r, "timestamp")
