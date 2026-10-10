import { Redirect } from 'expo-router';
import VerificationScreen from '@verification';
export default function Screen(){return VerificationScreen?<VerificationScreen/>:<Redirect href="/(tabs)/today"/>;}
