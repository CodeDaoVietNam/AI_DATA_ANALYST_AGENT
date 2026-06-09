import { useState } from "react";
import type { EcommerceOverview, RecordRow, SummaryWrapper } from "../types";
import {
  getEcommerceOverview,
  getRevenueByCategory,
  getRevenueByMonth,
  getTopStates,
  getTopSkus,
  getRevenueBySize,
  getCategoryCancellation,
  getFulfilment,
  getCourier,
  getPromotion,
  getB2B,
  getTopCities,
  getStateCancellation
} from "../api";

export function useEcommerceData() {
  const [ecommerce, setEcommerce] = useState<EcommerceOverview | null>(null);
  const [categoryRows, setCategoryRows] = useState<RecordRow[]>([]);
  const [monthRows, setMonthRows] = useState<RecordRow[]>([]);
  const [stateRows, setStateRows] = useState<RecordRow[]>([]);
  const [skuRows, setSkuRows] = useState<RecordRow[]>([]);
  const [sizeRows, setSizeRows] = useState<RecordRow[]>([]);
  const [categoryRiskRows, setCategoryRiskRows] = useState<RecordRow[]>([]);
  const [fulfilmentRows, setFulfilmentRows] = useState<RecordRow[]>([]);
  const [courierRows, setCourierRows] = useState<RecordRow[]>([]);
  const [promotionSummary, setPromotionSummary] = useState<SummaryWrapper["summary"] | null>(null);
  const [b2bSummary, setB2bSummary] = useState<SummaryWrapper["summary"] | null>(null);
  const [cityRows, setCityRows] = useState<RecordRow[]>([]);
  const [stateRiskRows, setStateRiskRows] = useState<RecordRow[]>([]);

  async function fetchEcommerceData(datasetId: string) {
    const [
      ecommerceData,
      categoryData,
      monthData,
      stateData,
      skuData,
      sizeData,
      categoryRiskData,
      fulfilmentData,
      courierData,
      promotionData,
      b2bData,
      cityData,
      stateRiskData,
    ] = await Promise.all([
      getEcommerceOverview(datasetId).catch(() => null),
      getRevenueByCategory(datasetId).catch(() => ({ items: [] })),
      getRevenueByMonth(datasetId).catch(() => ({ items: [] })),
      getTopStates(datasetId).catch(() => ({ items: [] })),
      getTopSkus(datasetId).catch(() => ({ items: [] })),
      getRevenueBySize(datasetId).catch(() => ({ items: [] })),
      getCategoryCancellation(datasetId).catch(() => ({ items: [] })),
      getFulfilment(datasetId).catch(() => ({ items: [] })),
      getCourier(datasetId).catch(() => ({ items: [] })),
      getPromotion(datasetId).catch(() => ({ summary: null })),
      getB2B(datasetId).catch(() => ({ summary: null })),
      getTopCities(datasetId).catch(() => ({ items: [] })),
      getStateCancellation(datasetId).catch(() => ({ items: [] })),
    ]);

    setEcommerce(ecommerceData);
    setCategoryRows(categoryData.items);
    setMonthRows(monthData.items);
    setStateRows(stateData.items);
    setSkuRows(skuData.items);
    setSizeRows(sizeData.items);
    setCategoryRiskRows(categoryRiskData.items);
    setFulfilmentRows(fulfilmentData.items);
    setCourierRows(courierData.items);
    setPromotionSummary(promotionData.summary);
    setB2bSummary(b2bData.summary);
    setCityRows(cityData.items);
    setStateRiskRows(stateRiskData.items);
  }

  function resetEcommerceData() {
    setEcommerce(null);
    setCategoryRows([]);
    setMonthRows([]);
    setStateRows([]);
    setSkuRows([]);
    setSizeRows([]);
    setCategoryRiskRows([]);
    setFulfilmentRows([]);
    setCourierRows([]);
    setPromotionSummary(null);
    setB2bSummary(null);
    setCityRows([]);
    setStateRiskRows([]);
  }

  return {
    ecommerce,
    categoryRows,
    monthRows,
    stateRows,
    skuRows,
    sizeRows,
    categoryRiskRows,
    fulfilmentRows,
    courierRows,
    promotionSummary,
    b2bSummary,
    cityRows,
    stateRiskRows,
    fetchEcommerceData,
    resetEcommerceData,
  };
}
