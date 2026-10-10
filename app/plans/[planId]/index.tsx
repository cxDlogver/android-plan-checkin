import { useLocalSearchParams } from 'expo-router';
import PlanDetail from '../../../src/features/plan-detail';
export default function Screen(){const {planId}=useLocalSearchParams<{planId:string}>();return <PlanDetail planId={planId}/>;}
